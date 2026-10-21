from django.urls import path
from .views import (
    AboutView,
    AddToCartView,
    CartView,
    CategoryView,
    HomeView,
    MessageView,
    ProductDetailView,
    remove_from_cart,
    update_cart_item,
)


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('categories/', CategoryView.as_view(), name='category'),
    path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('about/', AboutView.as_view(), name='about'),
    path('contact/', MessageView.as_view(), name='contact'),
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/<int:pk>/', AddToCartView.as_view(), name='add_to_cart'),
    path('cart/update/<int:pk>/', update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:pk>/', remove_from_cart, name='remove_from_cart'),
]