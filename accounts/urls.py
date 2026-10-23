from django.urls import path
from . import views
from .views import (
    CustomerRegistrationView,
    PasswordResetOTPVerificationView,
    PasswordResetResendOTPView,
    PasswordResetSetPasswordView,
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
        views.CustomerPasswordResetView.as_view(),
        name='reset_password'
    ),
    path(
        'password-reset/verify/',
        PasswordResetOTPVerificationView.as_view(),
        name='password_reset_verify',
    ),
    path(
        'password-reset/resend/',
        PasswordResetResendOTPView.as_view(),
        name='password_reset_resend',
    ),
    path(
        'password-reset/set-password/',
        PasswordResetSetPasswordView.as_view(),
        name='password_reset_set_password',
    ),
    path(
        'password-reset/done/',
        views.PasswordResetDoneView.as_view(),
        name='password_reset_done'
    ),
    path(
        'password-reset-complete/',
        views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'
    ),
]