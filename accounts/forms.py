from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from invites.models import InviteLink


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
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
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