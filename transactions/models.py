import uuid

from django.db import models

from accounts.models import Customer
from products.models import Product


class Transaction(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = 'cod', 'Cash on delivery'
        BANK_TRANSFER = 'bank_transfer', 'Bank transfer'
        PAYPAK = 'paypak', 'PayPak (manual confirmation)'
        PAY_NOW = 'pay_now', 'Pay now (simulated)'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    class OrderStatus(models.TextChoices):
        PLACED = 'placed', 'Placed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='transactions')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    order_status = models.CharField(
        max_length=12,
        choices=OrderStatus.choices,
        default=OrderStatus.PLACED,
    )
    shipping_name = models.CharField(max_length=200)
    shipping_phone = models.CharField(max_length=30)
    shipping_address = models.CharField(max_length=300)
    shipping_city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} - {self.customer}'


class TransactionItem(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'
