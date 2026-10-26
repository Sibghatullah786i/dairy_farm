from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import Customer

from .models import Cart, Category, ContactMessage, Product


User = get_user_model()


class ProductFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='cart-customer',
            email='cart@example.com',
            password='Cart-password-123!',
        )
        self.customer = Customer.objects.get(user=self.user)
        category = Category.objects.create(name='Dairy', slug='dairy')
        self.product = Product.objects.create(
            name='Fresh Milk',
            slug='fresh-milk',
            category=category,
            description='Fresh milk',
            price='10.00',
            image='products/fresh-milk.png',
            stock=5,
        )

    def test_root_url_redirects_to_the_canonical_homepage(self):
        response = self.client.get(reverse('root'))

        self.assertRedirects(
            response,
            reverse('home'),
            status_code=301,
            fetch_redirect_response=False,
        )

    def test_guest_add_to_cart_login_redirect_returns_to_product(self):
        add_url = reverse('add_to_cart', kwargs={'pk': self.product.pk})
        response = self.client.post(add_url)
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={add_url}',
            fetch_redirect_response=False,
        )

        login_response = self.client.post(
            reverse('login'),
            {
                'username': self.user.username,
                'password': 'Cart-password-123!',
                'next': add_url,
            },
        )
        self.assertRedirects(login_response, add_url, fetch_redirect_response=False)
        response = self.client.get(add_url)

        self.assertRedirects(
            response,
            reverse('product_detail', kwargs={'slug': self.product.slug}),
        )
        self.assertFalse(Cart.objects.exists())

    def test_guest_cart_mutation_redirects_do_not_end_in_405(self):
        item = Cart.objects.create(
            customer=self.customer,
            product=self.product,
            quantity=1,
        )
        for route_name in ('update_cart_item', 'remove_from_cart'):
            action_url = reverse(route_name, kwargs={'pk': item.pk})
            self.client.logout()
            self.client.get(action_url)
            self.client.post(
                reverse('login'),
                {
                    'username': self.user.username,
                    'password': 'Cart-password-123!',
                    'next': action_url,
                },
            )

            response = self.client.get(action_url)

            self.assertRedirects(response, reverse('cart'))

    def test_cart_page_does_not_create_a_missing_customer_profile(self):
        self.customer.delete()

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.filter(user=self.user).exists())

    def test_unknown_category_slug_returns_404(self):
        response = self.client.get(reverse('category'), {'slug': 'not-a-category'})

        self.assertEqual(response.status_code, 404)

    def test_contact_form_rejects_submissions_after_five_per_ip(self):
        data = {
            'name': 'Visitor',
            'email': 'visitor@example.com',
            'subject': 'Question',
            'message': 'Please contact me.',
            'website': '',
        }
        for _ in range(5):
            self.client.post(reverse('contact'), data)

        response = self.client.post(reverse('contact'), data)

        self.assertEqual(ContactMessage.objects.count(), 5)
        self.assertContains(response, 'Too many messages have been sent')
