from django.urls import path

from .views import CheckoutView, TransactionDetailView, TransactionListView


app_name = 'transactions'

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('', TransactionListView.as_view(), name='list'),
    path('<uuid:reference>/', TransactionDetailView.as_view(), name='detail'),
]
