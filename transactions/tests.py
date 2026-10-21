from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from accounts.models import Customer
from products.models import Cart, Category, Product

from .forms import CheckoutForm
from .models import Transaction, TransactionItem


class CheckoutRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer',
            password='Strong-pass-123',
        )
        self.customer = Customer.objects.get(user=self.user)
        category = Category.objects.create(name='Dairy', slug='dairy')
        self.product = Product.objects.create(
            name='Milk',
            slug='milk',
            category=category,
            description='Fresh milk',
            price=Decimal('250.00'),
            image='images/products/milk.png',
            stock=5,
        )
        Cart.objects.create(
            customer=self.customer,
            product=self.product,
            quantity=2,
        )
        self.client.force_login(self.user)
        self.checkout_data = {
            'shipping_name': 'Test Buyer',
            'shipping_phone': '03001234567',
            'shipping_address': '1 Dairy Road',
            'shipping_city': 'Multan',
            'payment_method': Transaction.PaymentMethod.CASH_ON_DELIVERY,
        }

    def test_checkout_reduces_stock_and_keeps_payment_pending(self):
        response = self.client.post('/transactions/checkout/', self.checkout_data)

        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        order = Transaction.objects.get()
        self.assertEqual(order.payment_status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(order.items.get().quantity, 2)
        self.assertFalse(Cart.objects.filter(customer=self.customer).exists())

    def test_checkout_rejects_invalid_phone_number(self):
        data = {**self.checkout_data, 'shipping_phone': 'abc'}

        response = self.client.post('/transactions/checkout/', data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_simulated_payment_is_not_offered_or_accepted_outside_debug(self):
        with override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver']):
            self.assertNotIn(
                Transaction.PaymentMethod.PAY_NOW,
                dict(CheckoutForm().fields['payment_method'].choices),
            )
            data = {
                **self.checkout_data,
                'payment_method': Transaction.PaymentMethod.PAY_NOW,
            }
            response = self.client.post('/transactions/checkout/', data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_cancelling_order_restores_stock_once(self):
        order = Transaction.objects.create(
            customer=self.customer,
            total_amount=Decimal('500.00'),
            payment_method=Transaction.PaymentMethod.CASH_ON_DELIVERY,
            shipping_name='Test Buyer',
            shipping_phone='03001234567',
            shipping_address='1 Dairy Road',
            shipping_city='Multan',
        )
        TransactionItem.objects.create(
            transaction=order,
            product=self.product,
            product_name=self.product.name,
            quantity=2,
            unit_price=self.product.price,
        )
        Product.objects.filter(pk=self.product.pk).update(stock=3)

        order.order_status = Transaction.OrderStatus.CANCELLED
        order.save(update_fields=['order_status'])
        order.save(update_fields=['order_status'])

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
