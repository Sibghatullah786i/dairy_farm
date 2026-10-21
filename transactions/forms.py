from django import forms

from .models import Transaction


class CheckoutForm(forms.Form):
    shipping_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
    )
    shipping_phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
    )
    shipping_address = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'autocomplete': 'street-address',
        }),
    )
    shipping_city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'address-level2',
        }),
    )
    payment_method = forms.ChoiceField(
        choices=[
            choice
            for choice in Transaction.PaymentMethod.choices
            if choice[0] != Transaction.PaymentMethod.PAYPAK
        ],
        widget=forms.RadioSelect,
    )
