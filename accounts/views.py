from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .forms import CustomerLoginForm, CustomerProfileForm, CustomerRegistrationForm
from .models import get_customer_for_user


class CustomerRegistrationView(View):
    def get(self, request):
        form = CustomerRegistrationForm()
        return render(request, 'accounts/registration.html', {'form': form})

    def post(self, request):
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Your account has been created.')
            return redirect('profile')
        return render(request, 'accounts/registration.html', {'form': form})


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        form = CustomerProfileForm(instance=get_customer_for_user(request.user))
        return render(request, 'accounts/profile.html', {'form': form})

    def post(self, request):
        form = CustomerProfileForm(
            request.POST,
            instance=get_customer_for_user(request.user),
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile saved successfully')
            return redirect('profile')
        messages.error(request, 'Correct the errors below.')
        return render(request, 'accounts/profile.html', {'form': form})


class UserLoginView(View):
    def get(self, request):
        form = CustomerLoginForm()
        return render(request, 'accounts/login.html', {
            'form': form,
            'next': request.GET.get('next', ''),
        })

    def post(self, request):
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('home')

        messages.error(request, 'Invalid username or password.')
        return render(request, 'accounts/login.html', {
            'form': form,
            'next': request.POST.get('next', ''),
        })


class UserLogoutView(View):
    def post(self, request):
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('home')
