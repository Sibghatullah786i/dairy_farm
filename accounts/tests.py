from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.test import TestCase

from .admin import AdminUserChangeForm
from .forms import CustomerRegistrationForm
from .models import Customer


class AccountRegressionTests(TestCase):
    def test_missing_customer_profile_is_recreated_across_site_pages(self):
        user = User.objects.create_user(username='profileless', password='Strong-pass-123')
        Customer.objects.filter(user=user).delete()
        self.client.force_login(user)

        for url in ('/', '/products/cart/', '/accounts/profile/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertTrue(Customer.objects.filter(user=user).exists())

    def test_logout_requires_post(self):
        user = User.objects.create_user(username='logout-user', password='Strong-pass-123')
        self.client.force_login(user)

        self.assertEqual(self.client.get('/accounts/logout/').status_code, 405)
        self.assertTrue(self.client.get('/accounts/profile/').wsgi_request.user.is_authenticated)
        self.assertEqual(self.client.post('/accounts/logout/').status_code, 302)

    def test_registration_rejects_case_insensitive_duplicate_usernames(self):
        User.objects.create_user(username='alice', password='Strong-pass-123')
        form = CustomerRegistrationForm(data={
            'username': 'ALICE',
            'email': 'alice2@example.com',
            'password1': 'Strong-pass-123',
            'password2': 'Strong-pass-123',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_admin_rejects_case_insensitive_duplicate_email(self):
        user = User.objects.create_user(
            username='existing-user',
            email='existing@example.com',
            password='Strong-pass-123',
        )
        other_user = User.objects.create_user(
            username='other-user',
            email='other@example.com',
            password='Strong-pass-123',
        )
        form = AdminUserChangeForm(instance=other_user)
        form.cleaned_data = {'email': 'EXISTING@example.com'}

        with self.assertRaises(ValidationError):
            form.clean_email()
