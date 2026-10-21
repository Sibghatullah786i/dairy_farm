from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import ContactMessageForm
from .models import Cart, Category, Product
from accounts.models import Customer


class HomeView(ListView):
    model = Product
    template_name = 'products/home.html'
    context_object_name = 'products'

    def get_queryset(self):
        products = Product.objects.filter(is_active=True).select_related('category')
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            products = products.filter(name__icontains=search_query)
        return products

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search_query'] = self.request.GET.get('search', '').strip()
        return context


class CategoryView(View):
    def get(self, request):
        category_slug = request.GET.get('slug')
        categories = Category.objects.all()

        if category_slug:
            category_products = Product.objects.filter(
                category__slug=category_slug,
                is_active=True,
            ).select_related('category')
        else:
            category_products = Product.objects.filter(is_active=True).select_related('category')

        return render(request, 'products/category.html', {
            'category_products': category_products,
            'categories': categories,
            'selected_slug': category_slug,
        })


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class AboutView(View):
    def get(self, request):
        return render(request, 'products/about.html')


class MessageView(View):
    def get(self, request):
        return render(request, 'products/contact.html', {'form': ContactMessageForm()})

    def post(self, request):
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            message = form.save()
            messages.success(
                request,
                f'Thank you, {message.name}. Your message has been sent successfully.',
            )
            return redirect('contact')
        return render(request, 'products/contact.html', {'form': form})


class CartView(View):
    def get(self, request):
        if request.user.is_authenticated:
            cart_items = Cart.objects.filter(
                customer=request.user.customer,
            ).select_related('product')
            for item in cart_items:
                item.line_total = item.product.price * item.quantity
            cart_total = sum(
                (item.line_total for item in cart_items),
                start=Decimal('0.00'),
            )
        else:
            cart_items = []
            cart_total = Decimal('0.00')

        return render(request, 'products/cart.html', {
            'cart_items': cart_items,
            'cart_total': cart_total,
            'categories': Category.objects.all(),
        })


class AddToCartView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            quantity = int(request.POST.get('quantity', '1'))
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid quantity.')
            return redirect('product_detail', pk=pk)

        if quantity < 1 or quantity > 10:
            messages.error(request, 'Quantity must be between 1 and 10.')
            return redirect('product_detail', pk=pk)

        customer = request.user.customer
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(pk=customer.pk)
            product = get_object_or_404(
                Product.objects.select_for_update(),
                pk=pk,
                is_active=True,
            )
            if product.stock < 1:
                messages.error(request, f'{product.name} is out of stock.')
                return redirect('product_detail', pk=product.pk)
            if quantity > product.stock:
                messages.error(request, f'Only {product.stock} of {product.name} are available.')
                return redirect('product_detail', pk=product.pk)

            cart_item, created = Cart.objects.get_or_create(
                customer=customer,
                product=product,
            )
            new_quantity = quantity if created else cart_item.quantity + quantity
            if new_quantity > 10:
                messages.error(request, 'A product is limited to 10 per cart.')
                return redirect('product_detail', pk=product.pk)
            if new_quantity > product.stock:
                messages.error(request, f'Only {product.stock} of {product.name} are available.')
                return redirect('product_detail', pk=product.pk)

            cart_item.quantity = new_quantity
            cart_item.save(update_fields=['quantity'])

        if request.POST.get('action') == 'buy_now':
            messages.success(request, f'{product.name} is in your cart. Review your order below.')
        else:
            messages.success(request, f'Added {quantity} x {product.name} to your cart.')
        return redirect('cart')


@login_required
@require_POST
def update_cart_item(request, pk):
    try:
        quantity = int(request.POST.get('quantity', ''))
    except (TypeError, ValueError):
        messages.error(request, 'Please enter a valid quantity.')
        return redirect('cart')

    if quantity < 1 or quantity > 10:
        messages.error(request, 'Quantity must be between 1 and 10.')
        return redirect('cart')

    customer = request.user.customer
    with transaction.atomic():
        Customer.objects.select_for_update().get(pk=customer.pk)
        cart_item = get_object_or_404(
            Cart.objects.select_for_update().select_related('product'),
            pk=pk,
            customer=customer,
        )
        product = Product.objects.select_for_update().get(pk=cart_item.product_id)
        if quantity > product.stock:
            messages.error(
                request,
                f'Only {product.stock} of {product.name} are available.',
            )
            return redirect('cart')
        cart_item.quantity = quantity
        cart_item.save(update_fields=['quantity'])
    messages.success(request, f'Updated {cart_item.product.name} quantity.')
    return redirect('cart')


@login_required
@require_POST
def remove_from_cart(request, pk):
    customer = request.user.customer
    with transaction.atomic():
        Customer.objects.select_for_update().get(pk=customer.pk)
        cart_item = get_object_or_404(
            Cart.objects.select_for_update(),
            pk=pk,
            customer=customer,
        )
        cart_item.delete()
    messages.success(request, 'Item removed from your cart.')
    return redirect('cart')
