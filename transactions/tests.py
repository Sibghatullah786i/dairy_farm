from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import Customer
from products.models import Cart, Category, Product

from .admin import TransactionAdmin, TransactionItemInline
from .models import Transaction, TransactionItem


User = get_user_model()


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='Buyer-password-123!',
        )
        self.customer = Customer.objects.get(user=self.user)
        category = Category.objects.create(name='Dairy', slug='dairy')
        self.product = Product.objects.create(
            name='Fresh Milk',
            slug='fresh-milk',
            category=category,
            description='Fresh milk',
            price=Decimal('10.00'),
            image='products/fresh-milk.png',
            stock=5,
        )
        self.cart_item = Cart.objects.create(
            customer=self.customer,
            product=self.product,
            quantity=2,
        )
        self.client.force_login(self.user)
        self.checkout_url = reverse('transactions:checkout')
        self.checkout_data = {
            'displayed_total': '20.00',
            'shipping_name': 'Buyer',
            'shipping_phone': '03001234567',
            'shipping_address': '1 Farm Road',
            'shipping_city': 'Lahore',
            'payment_method': Transaction.PaymentMethod.CASH_ON_DELIVERY,
        }

    def test_checkout_rejects_a_price_change_since_the_page_was_shown(self):
        self.client.get(self.checkout_url)
        Product.objects.filter(pk=self.product.pk).update(price=Decimal('12.00'))

        response = self.client.post(self.checkout_url, self.checkout_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'order total has changed')
        self.assertEqual(
            response.context['form']['displayed_total'].value(),
            '24.00',
        )
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(Cart.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

        response = self.client.post(
            self.checkout_url,
            {
                **self.checkout_data,
                'displayed_total': response.context['form']['displayed_total'].value(),
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Transaction.objects.get()
        self.assertEqual(order.total_amount, Decimal('24.00'))

    def test_checkout_charges_the_confirmed_total_and_decrements_stock(self):
        response = self.client.post(
            self.checkout_url,
            {
                **self.checkout_data,
                'displayed_total': '20.00',
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Transaction.objects.get()
        self.assertEqual(order.total_amount, Decimal('20.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(Cart.objects.exists())

    def test_bulk_cancellation_restocks_once(self):
        order = Transaction.objects.create(
            customer=self.customer,
            total_amount=Decimal('20.00'),
            payment_method=Transaction.PaymentMethod.CASH_ON_DELIVERY,
            shipping_name='Buyer',
            shipping_phone='03001234567',
            shipping_address='1 Farm Road',
            shipping_city='Lahore',
        )
        TransactionItem.objects.create(
            transaction=order,
            product=self.product,
            product_name=self.product.name,
            quantity=2,
            unit_price=self.product.price,
        )
        Product.objects.filter(pk=self.product.pk).update(stock=3)

        Transaction.objects.filter(pk=order.pk).update(
            order_status=Transaction.OrderStatus.CANCELLED,
        )
        Transaction.objects.filter(pk=order.pk).update(
            order_status=Transaction.OrderStatus.CANCELLED,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_model_cancellation_restocks_stock(self):
        order = Transaction.objects.create(
            customer=self.customer,
            total_amount=Decimal('10.00'),
            payment_method=Transaction.PaymentMethod.CASH_ON_DELIVERY,
            shipping_name='Buyer',
            shipping_phone='03001234567',
            shipping_address='1 Farm Road',
            shipping_city='Lahore',
        )
        TransactionItem.objects.create(
            transaction=order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=self.product.price,
        )
        Product.objects.filter(pk=self.product.pk).update(stock=4)

        order.order_status = Transaction.OrderStatus.CANCELLED
        order.save(update_fields=('order_status',))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_order_admin_disallows_deletion_and_inline_changes(self):
        request = RequestFactory().get('/admin/')
        transaction_admin = TransactionAdmin(Transaction, admin.site)
        item_inline = TransactionItemInline(TransactionItem, admin.site)

        self.assertFalse(transaction_admin.has_delete_permission(request))
        self.assertFalse(item_inline.can_delete)
        self.assertFalse(item_inline.has_add_permission(request))

    def test_customers_cannot_view_another_customers_order(self):
        order = Transaction.objects.create(
            customer=self.customer,
            total_amount=Decimal('20.00'),
            payment_method=Transaction.PaymentMethod.CASH_ON_DELIVERY,
            shipping_name='Buyer',
            shipping_phone='03001234567',
            shipping_address='1 Farm Road',
            shipping_city='Lahore',
        )
        other_user = User.objects.create_user(
            username='other-buyer',
            email='other@example.com',
            password='Other-password-123!',
        )
        self.client.force_login(other_user)

        response = self.client.get(
            reverse('transactions:detail', kwargs={'reference': order.reference}),
        )

        self.assertEqual(response.status_code, 404)
