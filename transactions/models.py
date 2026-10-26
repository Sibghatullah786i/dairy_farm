import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Sum

from accounts.models import Customer
from products.models import Product


class TransactionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if 'order_status' not in kwargs:
            return super().update(**kwargs)

        new_status = kwargs['order_status']
        if not isinstance(new_status, str):
            raise ValidationError(
                'Bulk order status updates must use a literal status value.',
            )
        valid_statuses = {value for value, _ in Transaction.OrderStatus.choices}
        if new_status not in valid_statuses:
            raise ValidationError('Select a valid order status.')

        with transaction.atomic():
            previous_statuses = list(
                self.select_for_update().values_list('order_status', flat=True)
            )
            if (
                new_status != Transaction.OrderStatus.CANCELLED
                and Transaction.OrderStatus.CANCELLED in previous_statuses
            ):
                raise ValidationError('A cancelled order cannot be reopened.')
            if (
                new_status == Transaction.OrderStatus.CANCELLED
                and Transaction.OrderStatus.DELIVERED in previous_statuses
            ):
                raise ValidationError('A delivered order cannot be cancelled.')

            if new_status == Transaction.OrderStatus.CANCELLED:
                order_ids = list(
                    self.exclude(
                        order_status=Transaction.OrderStatus.CANCELLED,
                    ).values_list('pk', flat=True)
                )
                quantities = (
                    TransactionItem.objects.filter(
                        transaction_id__in=order_ids,
                        product__isnull=False,
                    )
                    .values('product_id')
                    .annotate(total_quantity=Sum('quantity'))
                )
                for item in quantities:
                    Product.objects.filter(pk=item['product_id']).update(
                        stock=F('stock') + item['total_quantity'],
                    )

            return super().update(**kwargs)


class Transaction(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = 'cod', 'Cash on delivery'
        BANK_TRANSFER = 'bank_transfer', 'Bank transfer'
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

    objects = TransactionQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        status_is_saved = (
            kwargs.get('update_fields') is None
            or 'order_status' in kwargs['update_fields']
        )
        if self._state.adding or not status_is_saved:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            previous_status = (
                type(self).objects.select_for_update()
                .filter(pk=self.pk)
                .values_list('order_status', flat=True)
                .first()
            )
            if (
                previous_status == self.OrderStatus.CANCELLED
                and self.order_status != self.OrderStatus.CANCELLED
            ):
                raise ValidationError('A cancelled order cannot be reopened.')
            if (
                previous_status == self.OrderStatus.DELIVERED
                and self.order_status == self.OrderStatus.CANCELLED
            ):
                raise ValidationError('A delivered order cannot be cancelled.')
            super().save(*args, **kwargs)
            if (
                previous_status != self.OrderStatus.CANCELLED
                and self.order_status == self.OrderStatus.CANCELLED
            ):
                for product_id, quantity in self.items.filter(
                    product__isnull=False,
                ).values_list('product_id', 'quantity'):
                    Product.objects.filter(pk=product_id).update(
                        stock=F('stock') + quantity,
                    )

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
