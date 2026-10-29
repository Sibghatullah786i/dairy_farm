import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ecomm.utils import get_client_ip
from .models import PasswordResetOTP
from .views import (
    LOGIN_ATTEMPT_LIMIT,
    LOGIN_IP_LIMIT,
    OTP_MAX_ATTEMPTS,
    OTP_TTL,
    _increment_cache_counter,
)


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

    def test_failed_attempts_from_another_ip_do_not_lock_out_the_user(self):
        login_url = reverse('login')
        for _ in range(LOGIN_ATTEMPT_LIMIT):
            self.client.post(
                login_url,
                {
                    'username': self.user.username,
                    'password': 'incorrect',
                },
                REMOTE_ADDR='192.0.2.10',
            )

        response = self.client.post(
            login_url,
            {
                'username': self.user.username,
                'password': 'Correct-password-123!',
            },
            REMOTE_ADDR='198.51.100.10',
        )

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_ip_limit_allows_threshold_then_blocks(self):
        login_url = reverse('login')
        for attempt in range(LOGIN_IP_LIMIT):
            response = self.client.post(
                login_url,
                {'username': f'unrelated-{attempt % 5}', 'password': 'incorrect'},
                REMOTE_ADDR='192.0.2.20',
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            login_url,
            {'username': 'unrelated-0', 'password': 'incorrect'},
            REMOTE_ADDR='192.0.2.20',
        )
        self.assertContains(response, 'Too many login attempts')

    def test_account_limit_remains_strict(self):
        login_url = reverse('login')
        for _ in range(LOGIN_ATTEMPT_LIMIT):
            self.client.post(
                login_url,
                {'username': self.user.username, 'password': 'incorrect'},
                REMOTE_ADDR='192.0.2.30',
            )

        response = self.client.post(
            login_url,
            {'username': self.user.username, 'password': 'Correct-password-123!'},
            REMOTE_ADDR='192.0.2.30',
        )
        self.assertContains(response, 'Too many login attempts')

    def test_other_username_does_not_increment_account_counter(self):
        login_url = reverse('login')
        for _ in range(LOGIN_ATTEMPT_LIMIT):
            self.client.post(
                login_url,
                {'username': self.user.username, 'password': 'incorrect'},
                REMOTE_ADDR='192.0.2.40',
            )
        self.client.post(
            login_url,
            {'username': 'another-user', 'password': 'incorrect'},
            REMOTE_ADDR='192.0.2.40',
        )

        address_hash = hashlib.sha256(b'192.0.2.40').hexdigest()
        other_identity = hashlib.sha256(
            f'{address_hash}:another-user'.encode(),
        ).hexdigest()
        self.assertEqual(cache.get(f'login-ip-username:{other_identity}'), 1)
        login_identity = hashlib.sha256(
            f'{address_hash}:{self.user.username}'.encode(),
        ).hexdigest()
        self.assertEqual(cache.get(f'login-ip-username:{login_identity}'), 5)

    def test_ip_counters_are_independent_by_address(self):
        login_url = reverse('login')
        for _ in range(3):
            self.client.post(
                login_url,
                {'username': 'ip-one', 'password': 'incorrect'},
                REMOTE_ADDR='192.0.2.50',
            )
        self.client.post(
            login_url,
            {'username': 'ip-one', 'password': 'incorrect'},
            REMOTE_ADDR='198.51.100.50',
        )

        first_hash = hashlib.sha256(b'192.0.2.50').hexdigest()
        second_hash = hashlib.sha256(b'198.51.100.50').hexdigest()
        self.assertEqual(cache.get(f'login-ip:{first_hash}'), 3)
        self.assertEqual(cache.get(f'login-ip:{second_hash}'), 1)

    def test_shared_ip_users_are_not_blocked_at_old_limit(self):
        login_url = reverse('login')
        for attempt in range(LOGIN_ATTEMPT_LIMIT * 2):
            self.client.post(
                login_url,
                {'username': f'shared-user-{attempt}', 'password': 'incorrect'},
                REMOTE_ADDR='203.0.113.60',
            )

        response = self.client.post(
            login_url,
            {'username': self.user.username, 'password': 'Correct-password-123!'},
            REMOTE_ADDR='203.0.113.60',
        )
        self.assertRedirects(response, reverse('home'))

    def test_counter_expires(self):
        key = 'login-counter-expiry-test'
        self.assertEqual(_increment_cache_counter(key, 1), 1)
        time.sleep(1.1)
        self.assertEqual(_increment_cache_counter(key, 1), 1)

    def test_concurrent_counter_increments(self):
        key = 'login-counter-concurrency-test'
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(
                lambda _: _increment_cache_counter(key, 60),
                range(100),
            ))
        self.assertEqual(sorted(results)[-1], 100)
        self.assertEqual(cache.get(key), 100)


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
