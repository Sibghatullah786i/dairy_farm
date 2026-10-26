from django.contrib import admin
from django import forms

from .models import Transaction, TransactionItem


class TransactionAdminForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = '__all__'

    def clean_order_status(self):
        new_status = self.cleaned_data['order_status']
        if not self.instance.pk:
            return new_status
        current_status = Transaction.objects.filter(
            pk=self.instance.pk,
        ).values_list('order_status', flat=True).first()
        if (
            current_status == Transaction.OrderStatus.CANCELLED
            and new_status != current_status
        ):
            raise forms.ValidationError('A cancelled order cannot be reopened.')
        if (
            current_status == Transaction.OrderStatus.DELIVERED
            and new_status == Transaction.OrderStatus.CANCELLED
        ):
            raise forms.ValidationError('A delivered order cannot be cancelled.')
        return new_status


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 0
    can_delete = False
    readonly_fields = ['product', 'product_name', 'quantity', 'unit_price']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    form = TransactionAdminForm
    list_display = [
        'reference',
        'customer',
        'total_amount',
        'currency',
        'payment_method',
        'payment_status',
        'order_status',
        'created_at',
    ]
    list_filter = ['payment_method', 'payment_status', 'order_status', 'created_at']
    search_fields = ['reference', 'customer__user__username', 'shipping_name']
    readonly_fields = ['reference', 'customer', 'total_amount', 'currency', 'created_at']
    inlines = [TransactionItemInline]

    def has_delete_permission(self, request, obj=None):
        return False
