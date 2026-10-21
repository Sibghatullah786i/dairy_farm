from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import CustomerPasswordResetForm, CustomerSetPasswordForm
from .views import (
    CustomerRegistrationView,
    ProfileView,
    UserLoginView,
    UserLogoutView,
)

urlpatterns = [
    path(
        'register/',
        CustomerRegistrationView.as_view(),
        name='registration'
    ),

    path(
        'profile/',
        ProfileView.as_view(),
        name='profile'
    ),

    path(
        'login/',
        UserLoginView.as_view(),
        name='login'
    ),

    path('logout/', UserLogoutView.as_view(), name='logout'),

    path(
        'reset-password/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            form_class=CustomerPasswordResetForm
        ),
        name='reset_password'
    ),

    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            form_class=CustomerSetPasswordForm
        ),
        name='password_reset_confirm'
    ),

    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]