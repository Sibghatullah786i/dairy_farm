from django.contrib import admin
from .models import Customer

# Register your models here.
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'city','locality', 'mobile', 'zipcode')
    search_fields = ('user__username', 'name', 'city')
    list_filter = ('city',)
