from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import Customer, get_customer_for_user
from products.models import Cart, Product

from .forms import CheckoutForm
from .models import Transaction, TransactionItem


def cart_total(cart_items):
    return sum(
        (item.product.price * item.quantity for item in cart_items),
        start=Decimal('0.00'),
    )


def prepare_cart_items(customer):
    cart_items = list(
        Cart.objects.filter(customer=customer)
        .select_related('product')
        .order_by('pk')
    )
    for item in cart_items:
        item.line_total = item.product.price * item.quantity
    return cart_items


class CheckoutView(LoginRequiredMixin, View):
    template_name = 'transactions/checkout.html'

    def get(self, request):
        customer = get_customer_for_user(request.user)
        cart_items = prepare_cart_items(customer)
        if not cart_items:
            messages.info(request, 'Your cart is empty.')
            return redirect('cart')

        form = CheckoutForm(initial={
            'shipping_name': customer.name or request.user.get_full_name() or request.user.username,
            'shipping_phone': customer.mobile,
            'shipping_address': customer.locality,
            'shipping_city': customer.city,
        })
        return render(request, self.template_name, {
            'form': form,
            'cart_items': cart_items,
            'cart_total': cart_total(cart_items),
            'debug': settings.DEBUG,
        })

    def post(self, request):
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            customer = get_customer_for_user(request.user)
            cart_items = prepare_cart_items(customer)
            if not cart_items:
                messages.error(request, 'Your cart is empty. Add products before checking out.')
                return redirect('cart')
            return render(request, self.template_name, {
                'form': form,
                'cart_items': cart_items,
                'cart_total': cart_total(cart_items),
                'debug': settings.DEBUG,
            })

        customer = get_customer_for_user(request.user)
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(pk=customer.pk)
            cart_items = list(
                Cart.objects.filter(customer=customer)
                .select_for_update()
                .select_related('product')
                .order_by('pk')
            )
            for item in cart_items:
                item.line_total = item.product.price * item.quantity
            if not cart_items:
                messages.error(request, 'Your cart is empty. Add products before checking out.')
                return redirect('cart')

            locked_products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(
                    pk__in=[item.product_id for item in cart_items],
                )
            }
            for item in cart_items:
                product = locked_products.get(item.product_id)
                if product is None or not product.is_active:
                    messages.error(request, 'A product in your cart is no longer available.')
                    return redirect('cart')
                if item.quantity > 10:
                    messages.error(request, 'A product is limited to 10 per order.')
                    return redirect('cart')
                if item.quantity > product.stock:
                    messages.error(
                        request,
                        f'Only {product.stock} of {product.name} are available. '
                        'Update your cart before checking out.',
                    )
                    return redirect('cart')
                item.product = product

            stock_failure = None
            for item in cart_items:
                updated = Product.objects.filter(
                    pk=item.product_id,
                    is_active=True,
                    stock__gte=item.quantity,
                ).update(stock=F('stock') - item.quantity)
                if not updated:
                    stock_failure = item.product
                    break
            if stock_failure:
                transaction.set_rollback(True)
                messages.error(
                    request,
                    f'The available stock for {stock_failure.name} changed. '
                    'Please review your cart and try again.',
                )
                return redirect('cart')

            transaction_record = Transaction.objects.create(
                customer=customer,
                total_amount=cart_total(cart_items),
                payment_method=form.cleaned_data['payment_method'],
                payment_status=(
                    Transaction.PaymentStatus.PAID
                    if form.cleaned_data['payment_method'] == Transaction.PaymentMethod.PAY_NOW
                    else Transaction.PaymentStatus.PENDING
                ),
                shipping_name=form.cleaned_data['shipping_name'],
                shipping_phone=form.cleaned_data['shipping_phone'],
                shipping_address=form.cleaned_data['shipping_address'],
                shipping_city=form.cleaned_data['shipping_city'],
            )
            TransactionItem.objects.bulk_create([
                TransactionItem(
                    transaction=transaction_record,
                    product=item.product,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                )
                for item in cart_items
            ])
            Cart.objects.filter(pk__in=[item.pk for item in cart_items]).delete()

        messages.success(
            request,
            (
                'Your order was placed. The simulated payment is marked as paid.'
                if transaction_record.payment_status == Transaction.PaymentStatus.PAID
                else 'Your order was placed. Payment is recorded as pending until it is confirmed.'
            ),
        )
        return redirect(
            'transactions:detail',
            reference=transaction_record.reference,
        )


class TransactionListView(LoginRequiredMixin, View):
    def get(self, request):
        transactions = (
            Transaction.objects.filter(
                customer=get_customer_for_user(request.user),
            )
            .prefetch_related('items')
        )
        return render(request, 'transactions/transaction_list.html', {
            'transactions': transactions,
        })


class TransactionDetailView(LoginRequiredMixin, View):
    def get(self, request, reference):
        transaction_record = get_object_or_404(
            Transaction.objects.prefetch_related('items'),
            reference=reference,
            customer=get_customer_for_user(request.user),
        )
        return render(request, 'transactions/transaction_detail.html', {
            'transaction': transaction_record,
        })
