from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from invites.models import InviteLink


class UnifiedLoginForm(forms.Form):
    """Unified login form that supports both admin and regular user login"""
    
    username_email = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'input',
            'placeholder': 'Enter your username or email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Enter your password'
        })
    )
    
    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        username_email = self.cleaned_data.get('username_email')
        password = self.cleaned_data.get('password')
        
        if username_email and password:
            # Try to authenticate with username first
            self.user_cache = authenticate(self.request, username=username_email, password=password)
            
            # If that fails, try to find user by email and authenticate with username
            if self.user_cache is None:
                try:
                    user = User.objects.get(email=username_email)
                    self.user_cache = authenticate(self.request, username=user.username, password=password)
                except User.DoesNotExist:
                    pass
                except User.MultipleObjectsReturned:
                    # Handle multiple users with same email (shouldn't happen after cleanup)
                    users = User.objects.filter(email=username_email)
                    # Try to authenticate with each user until one works
                    for user in users:
                        self.user_cache = authenticate(self.request, username=user.username, password=password)
                        if self.user_cache:
                            break
            
            if self.user_cache is None:
                raise forms.ValidationError("Invalid username/email or password.")
            
            # Check if user is inactive
            if not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user_cache


class AdminLoginForm(AuthenticationForm):
    """Simple admin login with email and password"""
    
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your admin email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your password'
        })
    )
    
    def clean(self):
        email = self.cleaned_data.get('username')  # username field contains email
        password = self.cleaned_data.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
                self.user_cache = authenticate(self.request, username=user.username, password=password)
                if self.user_cache is None:
                    raise forms.ValidationError("Invalid email or password.")
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid email or password.")
            except User.MultipleObjectsReturned:
                # Handle multiple users with same email
                users = User.objects.filter(email=email)
                for user in users:
                    self.user_cache = authenticate(self.request, username=user.username, password=password)
                    if self.user_cache and self.user_cache.is_staff:
                        break
                if self.user_cache is None:
                    raise forms.ValidationError("Invalid email or password.")
        
        return self.cleaned_data


class UserLoginForm(forms.Form):
    """User login with email, password, and invite code"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your password'
        })
    )
    invite_code = forms.CharField(
        label="Invite Code",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your invite code'
        })
    )
    
    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        invite_code = self.cleaned_data.get('invite_code')
        
        if email and password and invite_code:
            # Validate invite code first
            try:
                invite = InviteLink.objects.get(code=invite_code)
                if not invite.is_valid():
                    raise forms.ValidationError("Invalid or expired invite code.")
            except InviteLink.DoesNotExist:
                raise forms.ValidationError("Invalid invite code.")
            
            # Check if user exists and authenticate
            try:
                user = User.objects.get(email=email)
                self.user_cache = authenticate(self.request, username=user.username, password=password)
                if self.user_cache is None:
                    raise forms.ValidationError("Invalid email or password.")
                
                # Check if user is associated with this invite
                if not user.is_staff and not hasattr(user, 'profile'):
                    raise forms.ValidationError("User profile not found.")
                    
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid email or password.")
            except User.MultipleObjectsReturned:
                # Handle multiple users with same email
                users = User.objects.filter(email=email)
                for user in users:
                    self.user_cache = authenticate(self.request, username=user.username, password=password)
                    if self.user_cache:
                        # Check if user is associated with this invite
                        if not user.is_staff and not hasattr(user, 'profile'):
                            continue  # Try next user
                        break
                if self.user_cache is None:
                    raise forms.ValidationError("Invalid email or password.")
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user_cache


class InviteRegistrationForm(UserCreationForm):
    """Registration form that requires a valid invite code"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Enter your last name'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Choose a username'
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Create a password'
        })
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Confirm your password'
        })
    )
    
    # Terms acceptance
    accept_terms = forms.BooleanField(
        required=True,
        label="I accept the Terms of Service and Privacy Policy",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
        })
    )
    
    # Age verification
    age_verification = forms.BooleanField(
        required=True,
        label="I verify that I am 18 years of age or older",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, invite_code=None, *args, **kwargs):
        self.invite_code = invite_code
        super().__init__(*args, **kwargs)
        
        # Validate invite code on form initialization
        if invite_code:
            try:
                self.invite = InviteLink.objects.get(code=invite_code)
                if not self.invite.is_valid():
                    raise forms.ValidationError("This invite link is no longer valid.")
            except InviteLink.DoesNotExist:
                raise forms.ValidationError("Invalid invite code.")
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("A user with this email address already exists. Please use a different email or try signing in.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError("This username is already taken. Please choose a different username.")
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            # Mark invite as used
            if hasattr(self, 'invite'):
                self.invite.mark_as_used(user)
                
                # Create referral approval record
                from invites.models import ReferralApproval
                ReferralApproval.objects.create(
                    invited_user=user,
                    inviter=self.invite.created_by
                )
        
        return user


class OTPVerificationForm(forms.Form):
    """Form for OTP verification"""
    
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'input text-center text-2xl tracking-widest',
            'placeholder': '000000',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric'
        }),
        help_text="Enter the 6-digit code sent to your email"
    )
    
    def __init__(self, email=None, *args, **kwargs):
        self.email = email
        super().__init__(*args, **kwargs)
    
    def clean_otp_code(self):
        otp_code = self.cleaned_data.get('otp_code')
        
        if not otp_code.isdigit():
            raise forms.ValidationError("OTP must contain only numbers.")
        
        return otp_code


class ResendOTPForm(forms.Form):
    """Form for resending OTP"""
    
    def __init__(self, email=None, *args, **kwargs):
        self.email = email
        super().__init__(*args, **kwargs)


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'input',
            'placeholder': 'Enter your email address'
        }),
        help_text="Enter the email address associated with your account"
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No account found with this email address.")
        elif User.objects.filter(email=email).count() > 1:
            # Multiple accounts with same email - this shouldn't happen after cleanup
            # But we'll handle it gracefully by continuing (password reset will work for any of them)
            pass
        return email


class PasswordResetConfirmForm(forms.Form):
    """Form for confirming password reset"""
    
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Enter your new password'
        }),
        min_length=8,
        help_text="Password must be at least 8 characters long"
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Confirm your new password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("The two password fields must match.")
        
        return cleaned_data