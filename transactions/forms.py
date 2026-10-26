from django import forms
from django.conf import settings
from accounts.models import PAKISTANI_MOBILE_VALIDATOR
from .models import Transaction


class CheckoutForm(forms.Form):
    displayed_total = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        widget=forms.HiddenInput,
    )
    shipping_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
    )
    shipping_phone = forms.CharField(
        max_length=30,
        validators=[PAKISTANI_MOBILE_VALIDATOR],
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
            if (
                settings.DEBUG
                or choice[0] != Transaction.PaymentMethod.PAY_NOW
            )
        ],
        widget=forms.RadioSelect,
    )
