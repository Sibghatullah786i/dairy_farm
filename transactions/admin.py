from django.contrib import admin

from .models import Transaction, TransactionItem


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 0
    readonly_fields = ['product_name', 'quantity', 'unit_price']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
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
