from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Customer


class CaseInsensitiveUserFields:
    def clean_username(self):
        username = self.cleaned_data['username'].strip().lower()
        if User.objects.filter(username__iexact=username).exclude(
            pk=self.instance.pk,
        ).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.pk,
        ).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email


class AdminUserChangeForm(CaseInsensitiveUserFields, UserChangeForm):
    pass


class AdminUserCreationForm(CaseInsensitiveUserFields, UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')


class CaseInsensitiveUserAdmin(UserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )


admin.site.unregister(User)
admin.site.register(User, CaseInsensitiveUserAdmin)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'city','locality', 'mobile', 'zipcode')
    search_fields = ('user__username', 'name', 'city')
    list_filter = ('city',)
