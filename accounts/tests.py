from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ecomm.utils import get_client_ip
from .models import PasswordResetOTP
from .views import LOGIN_ATTEMPT_LIMIT, OTP_MAX_ATTEMPTS, OTP_TTL


User = get_user_model()


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='reset-customer',
            email='customer@example.com',
            password='Old-password-123!',
        )

    @patch('accounts.views._send_reset_otp_in_background')
    def test_code_allows_five_attempts_and_expires_after_five_minutes(
        self,
        send_reset_email,
    ):
        with patch('accounts.views._new_otp', return_value='123456'):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(
                    reverse('reset_password'),
                    {'email': self.user.email},
                )
        self.assertEqual(send_reset_email.call_count, 1)
        otp = send_reset_email.call_args.args[1]
        reset_request = PasswordResetOTP.objects.get(user=self.user)
        self.assertEqual(OTP_TTL, timedelta(minutes=5))
        self.assertEqual(OTP_MAX_ATTEMPTS, 5)

        for _ in range(4):
            response = self.client.post(
                reverse('password_reset_verify'),
                {'otp': '000000'},
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('password_reset_verify'),
            {'otp': otp},
        )
        self.assertRedirects(response, reverse('password_reset_set_password'))
        reset_request.refresh_from_db()
        self.assertIsNotNone(reset_request.verified_at)

    @patch('accounts.views._send_reset_otp_in_background')
    def test_expired_code_is_rejected(self, send_reset_email):
        with patch('accounts.views._new_otp', return_value='123456'):
            self.client.post(
                reverse('reset_password'),
                {'email': self.user.email},
            )
        reset_request = PasswordResetOTP.objects.get(user=self.user)
        reset_request.created_at = timezone.now() - OTP_TTL - timedelta(seconds=1)
        reset_request.save(update_fields=('created_at',))

        response = self.client.post(
            reverse('password_reset_verify'),
            {'otp': '123456'},
        )

        self.assertEqual(response.status_code, 200)
        reset_request.refresh_from_db()
        self.assertIsNotNone(reset_request.invalidated_at)

    def test_reset_email_uses_the_configured_expiry(self):
        with patch('accounts.views.send_mail') as send_mail:
            from .views import _send_reset_otp

            _send_reset_otp(self.user.email, '123456')

        self.assertIn('expires in 5 minutes', send_mail.call_args.args[1])

    @patch('accounts.views._send_reset_otp_in_background')
    def test_unknown_email_still_performs_password_hash_work(self, send_reset_email):
        with patch('accounts.views.make_password', return_value='dummy-hash') as hash_otp:
            response = self.client.post(
                reverse('reset_password'),
                {'email': 'unknown@example.com'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(hash_otp.call_count, 1)
        send_reset_email.assert_not_called()


class LoginRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='login-customer',
            email='login@example.com',
            password='Correct-password-123!',
        )

    def test_login_is_limited_after_repeated_failures(self):
        login_url = reverse('login')
        for _ in range(LOGIN_ATTEMPT_LIMIT):
            self.client.post(
                login_url,
                {'username': self.user.username, 'password': 'incorrect'},
            )

        response = self.client.post(
            login_url,
            {'username': self.user.username, 'password': 'Correct-password-123!'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ClientIPTests(TestCase):
    def test_forwarded_ip_is_used_only_when_proxy_is_trusted(self):
        request = RequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR='198.51.100.10, 192.0.2.25',
            REMOTE_ADDR='192.0.2.1',
        )

        self.assertEqual(get_client_ip(request), '192.0.2.1')
        with override_settings(
            SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        ):
            self.assertEqual(get_client_ip(request), '192.0.2.25')
