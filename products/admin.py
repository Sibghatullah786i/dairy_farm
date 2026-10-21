
from django.contrib import admin
from .models import Cart, Category, ContactMessage, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug','picture']
    prepopulated_fields = {'slug': ('name',)}  # Auto-generates slug from name

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'is_active']
    list_filter = ['category', 'is_active']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['customer', 'product', 'quantity']
    search_fields = ['customer__user__username', 'product__name']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'name', 'email', 'created_at']
    search_fields = ['subject', 'name', 'email', 'message']
    readonly_fields = ['name', 'email', 'subject', 'message', 'created_at']