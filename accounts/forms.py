from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Customer
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm,SetPasswordForm





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

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email
    
class CustomerLoginForm(AuthenticationForm):
    username= forms.CharField(widget=forms.TextInput(attrs={'autofocus':'True','class':'form-control','placeholder':'Enter your username'}))
    
    password= forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Enter your Password'}))
    
class CustomerPasswordResetForm(PasswordResetForm):
    email=forms.EmailField(widget=forms.EmailInput(attrs={'auto-focus':'True','class':'form-control','placeholder':'Enter your registered email'}))

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email, is_active=True).count() > 1:
            raise forms.ValidationError(
                'This email address is linked to multiple accounts. Please contact support.'
            )
        return email
    
class CustomerSetPasswordForm(SetPasswordForm):
    new_password1=forms.CharField(label='New Password',widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Enter the new Password'}))
    new_password2=forms.CharField(label='New Password',widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Confirm new Password'}))
    
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
 
    
