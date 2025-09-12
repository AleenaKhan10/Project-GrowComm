from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import AdminLoginForm, UserLoginForm, InviteRegistrationForm, UnifiedLoginForm
from invites.models import InviteLink
from profiles.decorators import verified_user_required
from django.http import Http404, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from audittrack.utils import log_registration, log_signin, log_signout


class UnifiedLoginView(LoginView):
    """Unified login view for all users"""
    form_class = UnifiedLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.get_form().get_user()
        if user and user.is_staff:
            return reverse_lazy('admin:index')
        return reverse_lazy('communities:community_list')
    
    def form_valid(self, form):
        """Login user after successful form validation"""
        user = form.get_user()
        login(self.request, user)
        log_signin(user, "Unified login")
        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username/email or password.')
        return super().form_invalid(form)


def login_choice_view(request):
    """Redirect to unified login"""
    return redirect('accounts:unified_login')


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
        return reverse_lazy('communities:community_list')
    
    def form_valid(self, form):
        """Login user after successful form validation"""
        user = form.get_user()
        login(self.request, user)
        log_signin(user, "User login")
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
            
            # Set verification status based on who sent the invite
            profile = user.profile
            profile.invite_source = invite.created_by
            
            if invite.created_by.is_superuser:
                # Superadmin invite - verify immediately
                profile.is_verified = True
                profile.needs_referrals = False
                messages.success(request, f'Welcome to GrwComm, {user.first_name}! Your account is fully verified.')
            else:
                # Regular user invite - needs referrals
                profile.is_verified = False
                profile.needs_referrals = True
                messages.info(request, f'Welcome to GrwComm, {user.first_name}! You need 3 referrals to unlock all features.')
            
            profile.save()
            
            # Join community if invite has one
            if invite.community:
                from communities.models import CommunityMembership
                CommunityMembership.objects.create(
                    user=user,
                    community=invite.community,
                    role='member',
                    is_active=True
                )
            
            # Log registration event
            log_registration(user, f"Registered via invite from {invite.created_by.username}")
            
            # Automatically log in the user after registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                log_signin(user, "Initial login after registration")
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


@login_required
def logout_view(request):
    """Custom logout view with confirmation page"""
    if request.method == 'POST':
        log_signout(request.user, "Manual logout")
        logout(request)
        messages.success(request, 'You have been successfully signed out.')
        return render(request, 'accounts/logout_success.html')
    
    return render(request, 'accounts/logout.html')


def home_view(request):
    """Home page view - redirects based on authentication status"""
    if request.user.is_authenticated:
        return redirect('communities:community_list')
    return redirect('accounts:login')

def csrf_failure_view(request, reason=""):
    """Custom CSRF failure view with better error handling"""
    messages.error(request, 'Security verification failed. Please try again.')
    return redirect('accounts:login')
