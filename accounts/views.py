import hashlib
import logging
import secrets
import smtplib
import threading
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from ecomm.utils import get_client_ip
from .forms import (
    CustomerLoginForm,
    CustomerProfileForm,
    CustomerRegistrationForm,
    CustomerSetPasswordForm,
    OTPVerificationForm,
    PasswordResetRequestForm,
)
from .models import PasswordResetOTP, get_customer_for_user


logger = logging.getLogger(__name__)

OTP_TTL = timedelta(minutes=5)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_ATTEMPTS = 5
RESET_IP_LIMIT = 10
RESET_IP_WINDOW = 60 * 60
LOGIN_IP_USERNAME_LIMIT = 5
LOGIN_ATTEMPT_LIMIT = LOGIN_IP_USERNAME_LIMIT
LOGIN_IP_LIMIT = 50
LOGIN_ATTEMPT_WINDOW = 60 * 60
RESET_REQUEST_SESSION_KEY = 'password_reset_request_token'
RESET_VERIFIED_SESSION_KEY = 'password_reset_verified_token'
GENERIC_RESET_MESSAGE = (
    'If an account matches that email address, we will send a verification code. '
    'Check your email and enter the code below.'
)

User = get_user_model()


def _increment_cache_counter(key, timeout):
    """Atomically increment a cache counter, initializing it when necessary."""
    try:
        cache.add(key, 0, timeout=timeout)
        return cache.incr(key)
    except ValueError:
        # A backend can raise ValueError when an expiring entry disappears.
        if cache.add(key, 1, timeout=timeout):
            return 1
        try:
            return cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=timeout)
            return 1


def _request_token(request, session_key=RESET_REQUEST_SESSION_KEY):
    value = request.session.get(session_key)
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        return None


def _get_reset_request(request, session_key=RESET_REQUEST_SESSION_KEY):
    token = _request_token(request, session_key)
    if token is None:
        return None
    return PasswordResetOTP.objects.filter(
        request_token=token,
        user__is_active=True,
        invalidated_at__isnull=True,
        consumed_at__isnull=True,
    ).select_related('user').first()


def _rate_limited(request):
    address = get_client_ip(request)
    address_hash = hashlib.sha256(address.encode('utf-8')).hexdigest()
    key = f'password-reset-ip:{address_hash}'
    count = _increment_cache_counter(key, RESET_IP_WINDOW)
    return count > RESET_IP_LIMIT


def _new_otp():
    return f'{secrets.randbelow(1_000_000):06d}'


def _send_reset_otp(email, otp):
    try:
        send_mail(
            'Your password reset verification code',
            (
                f'Your password reset verification code is {otp}.\n\n'
                f'This code expires in {int(OTP_TTL.total_seconds() // 60)} minutes. '
                'If you did not request a '
                'password reset, you can ignore this email.'
            ),
            None,
            [email],
            fail_silently=False,
        )
    except (OSError, smtplib.SMTPException):
        logger.exception('Password reset OTP email delivery failed.')


def _send_reset_otp_in_background(email, otp):
    threading.Thread(
        target=_send_reset_otp,
        args=(email, otp),
        daemon=True,
    ).start()


class CustomerPasswordResetView(View):
    template_name = 'accounts/password_reset.html'
    verification_template_name = 'accounts/password_reset_verify.html'

    def get(self, request):
        return render(
            request,
            self.template_name,
            {'form': PasswordResetRequestForm()},
        )

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        token = uuid.uuid4()
        request.session[RESET_REQUEST_SESSION_KEY] = str(token)
        request.session.pop(RESET_VERIFIED_SESSION_KEY, None)

        email_request = None
        email_otp = None
        candidate_otp = _new_otp()
        otp_hash = make_password(candidate_otp)
        if not _rate_limited(request):
            with transaction.atomic():
                user = User.objects.select_for_update().filter(
                    email__iexact=form.cleaned_data['email'],
                    is_active=True,
                ).first()
                if user:
                    now = timezone.now()
                    active_request = PasswordResetOTP.objects.filter(
                        user=user,
                        invalidated_at__isnull=True,
                        consumed_at__isnull=True,
                        verified_at__isnull=True,
                    ).order_by('-created_at').first()
                    if (
                        active_request
                        and now - active_request.created_at < OTP_RESEND_COOLDOWN
                        and active_request.attempts < OTP_MAX_ATTEMPTS
                    ):
                        token = active_request.request_token
                    else:
                        PasswordResetOTP.objects.filter(
                            user=user,
                            invalidated_at__isnull=True,
                            consumed_at__isnull=True,
                        ).update(invalidated_at=now)
                        email_otp = candidate_otp
                        email_request = PasswordResetOTP.objects.create(
                            user=user,
                            request_token=token,
                            otp_hash=otp_hash,
                        )
                    request.session[RESET_REQUEST_SESSION_KEY] = str(token)

        if email_request:
            transaction.on_commit(
                lambda: _send_reset_otp_in_background(
                    email_request.user.email,
                    email_otp,
                )
            )

        return render(
            request,
            self.verification_template_name,
            {
                'form': OTPVerificationForm(),
                'generic_message': GENERIC_RESET_MESSAGE,
            },
        )


class PasswordResetOTPVerificationView(View):
    template_name = 'accounts/password_reset_verify.html'

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                'form': OTPVerificationForm(),
                'generic_message': GENERIC_RESET_MESSAGE,
            },
        )

    def post(self, request):
        form = OTPVerificationForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {'form': form, 'generic_message': GENERIC_RESET_MESSAGE},
            )

        with transaction.atomic():
            reset_request = _get_reset_request(request)
            if reset_request:
                reset_request = PasswordResetOTP.objects.select_for_update().filter(
                    pk=reset_request.pk,
                ).first()
            now = timezone.now()
            if not reset_request:
                form.add_error('otp', 'The code is invalid or expired. Request a new code.')
            elif reset_request.verified_at is not None:
                form.add_error('otp', 'The code is invalid or expired. Request a new code.')
            elif (
                reset_request.attempts >= OTP_MAX_ATTEMPTS
                or now - reset_request.created_at >= OTP_TTL
            ):
                reset_request.invalidated_at = now
                reset_request.save(update_fields=('invalidated_at',))
                form.add_error('otp', 'The code is invalid or expired. Request a new code.')
            elif not check_password(form.cleaned_data['otp'], reset_request.otp_hash):
                attempts_after_failure = reset_request.attempts + 1
                update_fields = {'attempts': F('attempts') + 1}
                if attempts_after_failure >= OTP_MAX_ATTEMPTS:
                    update_fields['invalidated_at'] = now
                PasswordResetOTP.objects.filter(pk=reset_request.pk).update(
                    **update_fields,
                )
                reset_request.refresh_from_db(fields=('attempts',))
                if reset_request.attempts >= OTP_MAX_ATTEMPTS:
                    form.add_error('otp', 'The code is invalid or expired. Request a new code.')
                else:
                    form.add_error('otp', 'The code is incorrect.')
            else:
                reset_request.verified_at = now
                reset_request.otp_hash = ''
                reset_request.save(update_fields=('verified_at', 'otp_hash'))
                request.session[RESET_VERIFIED_SESSION_KEY] = str(
                    reset_request.request_token,
                )
                return redirect('password_reset_set_password')

        return render(
            request,
            self.template_name,
            {'form': form, 'generic_message': GENERIC_RESET_MESSAGE},
        )


class PasswordResetResendOTPView(View):
    def post(self, request):
        email_request = None
        email_otp = None
        with transaction.atomic():
            reset_request = _get_reset_request(request)
            if reset_request:
                reset_request = PasswordResetOTP.objects.select_for_update().filter(
                    pk=reset_request.pk,
                ).first()
            now = timezone.now()
            can_resend = (
                reset_request is not None
                and reset_request.verified_at is None
                and reset_request.attempts < OTP_MAX_ATTEMPTS
                and now - reset_request.created_at >= OTP_RESEND_COOLDOWN
            )
            if can_resend and not _rate_limited(request):
                otp = _new_otp()
                reset_request.otp_hash = make_password(otp)
                reset_request.created_at = now
                reset_request.attempts = 0
                reset_request.save(
                    update_fields=('otp_hash', 'created_at', 'attempts'),
                )
                request.session.pop(RESET_VERIFIED_SESSION_KEY, None)
                email_request = reset_request
                email_otp = otp

        if email_request:
            transaction.on_commit(
                lambda: _send_reset_otp_in_background(
                    email_request.user.email,
                    email_otp,
                )
            )

        messages.info(
            request,
            'If a new code can be sent, it will arrive shortly. Please wait '
            'before requesting another code.',
        )
        return redirect('password_reset_verify')


class PasswordResetSetPasswordView(View):
    template_name = 'accounts/password_reset_set_password.html'

    def _verified_reset_request(self, request):
        reset_request = _get_reset_request(
            request,
            session_key=RESET_VERIFIED_SESSION_KEY,
        )
        if (
            reset_request is None
            or reset_request.verified_at is None
            or timezone.now() - reset_request.verified_at >= OTP_TTL
        ):
            return None
        return reset_request

    def get(self, request):
        reset_request = self._verified_reset_request(request)
        if reset_request is None:
            return redirect('reset_password')
        return render(
            request,
            self.template_name,
            {'form': CustomerSetPasswordForm(reset_request.user)},
        )

    def post(self, request):
        reset_request = self._verified_reset_request(request)
        if reset_request is None:
            return redirect('reset_password')

        form = CustomerSetPasswordForm(reset_request.user, request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = form.save()
        now = timezone.now()
        PasswordResetOTP.objects.filter(
            user=user,
            consumed_at__isnull=True,
            invalidated_at__isnull=True,
        ).update(
            consumed_at=now,
            invalidated_at=now,
            otp_hash='',
        )
        request.session.pop(RESET_REQUEST_SESSION_KEY, None)
        request.session.pop(RESET_VERIFIED_SESSION_KEY, None)
        return redirect('password_reset_complete')


class PasswordResetCompleteView(View):
    def get(self, request):
        return render(request, 'accounts/password_reset_complete.html')


class PasswordResetDoneView(View):
    def get(self, request):
        return render(
            request,
            'accounts/password_reset_done.html',
            {'verification_url': 'password_reset_verify'},
        )


class CustomerRegistrationView(View):
    def get(self, request):
        form = CustomerRegistrationForm()
        return render(request, 'accounts/registration.html', {'form': form})

    def post(self, request):
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Your account has been created.')
            return redirect('profile')
        return render(request, 'accounts/registration.html', {'form': form})


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        form = CustomerProfileForm(instance=get_customer_for_user(request.user))
        return render(request, 'accounts/profile.html', {'form': form})

    def post(self, request):
        form = CustomerProfileForm(
            request.POST,
            instance=get_customer_for_user(request.user),
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile saved successfully')
            return redirect('profile')
        messages.error(request, 'Correct the errors below.')
        return render(request, 'accounts/profile.html', {'form': form})


class UserLoginView(View):
    def get(self, request):
        form = CustomerLoginForm()
        return render(request, 'accounts/login.html', {
            'form': form,
            'next': request.GET.get('next', ''),
        })

    def post(self, request):
        username = request.POST.get('username', '').strip().lower()
        address_hash = hashlib.sha256(
            get_client_ip(request).encode('utf-8'),
        ).hexdigest()
        identity_hash = hashlib.sha256(
            f'{address_hash}:{username}'.encode('utf-8'),
        ).hexdigest()
        rate_keys = (
            f'login-ip:{address_hash}',
            f'login-ip-username:{identity_hash}',
        )
        ip_key, ip_username_key = rate_keys
        if (
            (cache.get(ip_key) or 0) >= LOGIN_IP_LIMIT
            or (cache.get(ip_username_key) or 0) >= LOGIN_IP_USERNAME_LIMIT
        ):
            messages.error(request, 'Too many login attempts. Please try again later.')
            return render(request, 'accounts/login.html', {
                'form': CustomerLoginForm(),
                'next': request.POST.get('next', ''),
            })

        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            cache.delete_many(rate_keys)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('home')

        for key in rate_keys:
            _increment_cache_counter(key, LOGIN_ATTEMPT_WINDOW)
        messages.error(request, 'Invalid username or password.')
        return render(request, 'accounts/login.html', {
            'form': form,
            'next': request.POST.get('next', ''),
        })


class UserLogoutView(View):
    def post(self, request):
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('home')
