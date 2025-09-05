from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.http import Http404
from .forms import AdminLoginForm, UserLoginForm, InviteRegistrationForm
from invites.models import InviteLink


def login_choice_view(request):
    """Main login page with admin/user choice"""
    if request.user.is_authenticated:
        return redirect('communities:user_list')
    return render(request, 'accounts/login_choice.html')


class AdminLoginView(LoginView):
    """Simple admin login with email/password"""
    form_class = AdminLoginForm
    template_name = 'accounts/admin_login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('admin:index')
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)
    
    def form_valid(self, form):
        user = form.get_user()
        if not user.is_staff:
            messages.error(self.request, 'Access denied. Admin privileges required.')
            return self.form_invalid(form)
        return super().form_valid(form)


class UserLoginView(LoginView):
    """User login requiring invite code validation"""
    form_class = UserLoginForm
    template_name = 'accounts/user_login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('communities:user_list')
    
    def form_valid(self, form):
        """Login user after successful form validation"""
        user = form.get_user()
        login(self.request, user)
        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid credentials or invite code.')
        return super().form_invalid(form)


def register_view(request, invite_code):
    """Invite-only registration view"""
    # Validate invite code first
    try:
        invite = InviteLink.objects.get(code=invite_code)
        if not invite.is_valid():
            messages.error(request, 'This invite link has expired or has already been used.')
            return redirect('accounts:login')
    except InviteLink.DoesNotExist:
        messages.error(request, 'Invalid invite link.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = InviteRegistrationForm(invite_code=invite_code, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Automatically log in the user after registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, f'Welcome to GrowCommunity, {user.first_name}!')
                return redirect('profiles:edit')  # Redirect to profile setup
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = InviteRegistrationForm(invite_code=invite_code)
    
    context = {
        'form': form,
        'invite': invite,
        'inviter_name': invite.created_by.first_name or invite.created_by.username,
    }
    return render(request, 'accounts/register.html', context)


def home_view(request):
    """Home page view - redirects based on authentication status"""
    if request.user.is_authenticated:
        return redirect('communities:user_list')
    return redirect('accounts:login')
