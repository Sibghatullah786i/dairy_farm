from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import CustomerRegistrationForm, CustomerLoginForm, CustomerProfileForm


class CustomerRegistrationView(View):
    def get(self, request):
        form = CustomerRegistrationForm()
        # Ensure you are using render(request, template_path, context)
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
        form = CustomerProfileForm(instance=request.user.customer)
        return render(request, 'accounts/profile.html', {'form': form})
        
    def post(self, request):
        form = CustomerProfileForm(request.POST, instance=request.user.customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile saved successfully')
            return redirect('profile')
        messages.error(request, 'Correct the errors below.')
        return render(request, 'accounts/profile.html', {'form': form})
            
        
class UserLoginView(View):
    def get(self, request):  # Ensure 'self' is 1st parameter
        form = CustomerLoginForm()
        return render(request, 'accounts/login.html', {
            'form': form,
            'next': request.GET.get('next', ''),
        })

    def post(self, request):  # Ensure 'self' is 1st parameter
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
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
    def get(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('home')
    