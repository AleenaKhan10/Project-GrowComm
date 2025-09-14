from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import AdminLoginForm, UserLoginForm, InviteRegistrationForm, UnifiedLoginForm, OTPVerificationForm, ResendOTPForm, PasswordResetRequestForm, PasswordResetConfirmForm
from .otp_service import OTPService
from .password_reset_service import PasswordResetService
from .models import EmailOTP, PasswordResetToken
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
            # Instead of creating user immediately, send OTP first
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password1']
            
            # Send OTP email
            success, result = OTPService.send_otp_email(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password,
                invite_code=invite_code
            )
            
            if success:
                messages.success(request, f'Verification code sent to {email}. Please check your email.')
                return redirect('accounts:verify_otp', email=email)
            else:
                messages.error(request, f'Failed to send verification email: {result}')
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


def verify_otp_view(request, email):
    """OTP verification view"""
    if request.method == 'POST':
        form = OTPVerificationForm(email=email, data=request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp_code']
            
            # Verify OTP
            success, result = OTPService.verify_otp(email, entered_otp)
            
            if success:
                # OTP verified successfully, create user
                otp_record = result
                
                # Get invite
                try:
                    invite = InviteLink.objects.get(code=otp_record.invite_code)
                except InviteLink.DoesNotExist:
                    messages.error(request, 'Invalid invite code.')
                    return redirect('accounts:login')
                
                # Create user
                user = User.objects.create_user(
                    username=otp_record.username,
                    email=otp_record.email,
                    first_name=otp_record.first_name,
                    last_name=otp_record.last_name,
                    password=None  # We'll set the password manually
                )
                
                # Set the password from the stored hash
                user.password = otp_record.password_hash
                user.save()
                
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
                
                # Mark invite as used
                invite.mark_as_used(user)
                
                # Create referral approval record
                from invites.models import ReferralApproval
                ReferralApproval.objects.create(
                    invited_user=user,
                    inviter=invite.created_by
                )
                
                # Log registration event
                log_registration(user, f"Registered via invite from {invite.created_by.username}")
                
                # Clean up OTP record
                otp_record.delete()
                
                # Automatically log in the user
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                log_signin(user, "Initial login after registration")
                return redirect('profiles:edit')  # Redirect to profile setup
                
            else:
                # OTP verification failed
                messages.error(request, result)
        else:
            messages.error(request, 'Please enter a valid 6-digit code.')
    else:
        form = OTPVerificationForm(email=email)
    
    # Get invite code for links
    otp_record = EmailOTP.objects.filter(email=email, is_verified=False).order_by('-created_at').first()
    invite_code = otp_record.invite_code if otp_record else None
    
    context = {
        'form': form,
        'email': email,
        'invite_code': invite_code,
    }
    return render(request, 'accounts/verify_otp.html', context)


def resend_otp_view(request):
    """Resend OTP view"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            success, message = OTPService.resend_otp(email)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect('accounts:verify_otp', email=email)
    
    return redirect('accounts:login')


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


def password_reset_request_view(request):
    """Password reset request view"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Send reset email
            success, message = PasswordResetService.send_reset_email(email)
            
            if success:
                messages.success(request, 'If an account with this email exists, you\'ll receive password reset instructions shortly.')
                return redirect('accounts:login')
            else:
                messages.error(request, message)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordResetRequestForm()
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/password_reset_request.html', context)


def password_reset_confirm_view(request, token):
    """Password reset confirmation view"""
    # Verify token first
    success, result = PasswordResetService.verify_token(token)
    
    if not success:
        messages.error(request, result)
        return redirect('accounts:login')
    
    reset_token = result
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            
            # Reset password
            success, message = PasswordResetService.reset_password(token, new_password)
            
            if success:
                messages.success(request, 'Your password has been reset successfully. You can now sign in with your new password.')
                return redirect('accounts:login')
            else:
                messages.error(request, message)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordResetConfirmForm()
    
    context = {
        'form': form,
        'token': token,
        'user_email': reset_token.user.email,
    }
    return render(request, 'accounts/password_reset_confirm.html', context)
