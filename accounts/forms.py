from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User

from .models import Customer


class CustomerRegistrationForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'autofocus': 'True', 'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_username(self):
        username = super().clean_username()
        if not username:
            return username
        normalized_username = username.strip().lower()
        if User.objects.filter(username__iexact=normalized_username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return normalized_username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email

class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'Enter your username',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your Password',
        }),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            return username
        return (
            User.objects.filter(username__iexact=username)
            .values_list('username', flat=True)
            .first()
            or username
        )
    
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
        }),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class OTPVerificationForm(forms.Form):
    otp = forms.RegexField(
        regex=r'^\d{6}$',
        error_messages={'invalid': 'Enter the 6-digit code from your email.'},
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '6-digit code',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'maxlength': '6',
        }),
    )


class CustomerSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a new password',
            'autocomplete': 'new-password',
        }),
    )
    new_password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm the new password',
            'autocomplete': 'new-password',
        }),
    )

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'locality', 'city', 'mobile', 'zipcode']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'locality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House no, Street name'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '03001234567'}),
            'zipcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal code'}),
        }
