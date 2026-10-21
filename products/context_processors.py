from django.db.models import Sum
from accounts.models import get_customer_for_user
from .models import Cart, Category

def cart_count(request):
    if request.user.is_authenticated:
        count = Cart.objects.filter(
            customer=get_customer_for_user(request.user),
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0
    else:
        count = 0
        
    return {
        'cart_count': count,
        'categories': Category.objects.all(),
    }