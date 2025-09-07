from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Referral
from messaging.models import CustomMessageSlot, UserMessageSettings


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    
    # User fields
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
            'placeholder': 'Enter your last name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
            'placeholder': 'Enter your email address'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'gender', 'city', 'country', 'bio', 'company', 'team', 'organization_level',
            'schools', 'tags', 'phone_number', 'name_visibility'
        ]
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-700 file:mr-4 file:py-3 file:px-4 file:rounded file:border file:border-gray-300 file:text-sm file:font-medium file:bg-white file:text-gray-700 hover:file:bg-gray-50 transition-colors',
                'accept': 'image/*'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors min-h-[100px]',
                'rows': 4,
                'placeholder': 'Tell us about yourself, your interests, and what you bring to the community...'
            }),
            'company': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
                'placeholder': 'Your current company or organization'
            }),
            'team': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
                'placeholder': 'Your team or department'
            }),
            'organization_level': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
                'placeholder': 'Enter your city'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
                'placeholder': 'Enter your country'
            }),
            'schools': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors min-h-[100px]',
                'rows': 3,
                'placeholder': 'Enter schools/universities (one per line or comma-separated)\nExample: Harvard University, MIT, Stanford Business School'
            }),
            'tags': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors min-h-[100px]',
                'rows': 3,
                'placeholder': 'Enter skills, interests, or expertise areas (comma-separated)\nExample: Python, Data Science, Startup, Machine Learning, Product Management'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded text-black placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
                'placeholder': 'Your phone number (optional)'
            }),
            'name_visibility': forms.Select(attrs={
                'class': 'w-3/5 px-4 py-3 bg-white border border-gray-300 rounded text-black focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate user fields
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user and User.objects.filter(email=email).exclude(id=self.user.id).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Update user fields
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            if commit:
                self.user.save()
        
        if commit:
            profile.save()
        return profile


class ProfileSearchForm(forms.Form):
    """Form for searching and filtering user profiles"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-cyan-500 focus:border-transparent h-8',
            'placeholder': 'Search by name, company, skills...'
        })
    )
    organization_level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Levels')] + UserProfile.ORGANIZATION_LEVELS,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-cyan-500 focus:border-transparent h-8'
        })
    )
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-cyan-500 focus:border-transparent h-8',
            'placeholder': 'Filter by tags...'
        })
    )


class SendReferralForm(forms.ModelForm):
    """Form for sending referrals to new users"""
    
    recipient_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input',
            'placeholder': 'Enter email address to refer'
        }),
        help_text="Email address of the person you want to refer to GrwCommunity"
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'input',
            'rows': 4,
            'placeholder': 'Optional message to include with your referral...'
        }),
        required=False,
        max_length=500,
        help_text="Optional personal message (max 500 characters)"
    )
    
    class Meta:
        model = Referral
        fields = ['recipient_email']
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_recipient_email(self):
        email = self.cleaned_data.get('recipient_email')
        
        if not email:
            return email
        
        # Check if user is trying to refer themselves
        if self.user and self.user.email == email:
            raise forms.ValidationError("You cannot refer yourself.")
        
        # Check if this email is already referred by this user
        if self.user and Referral.objects.filter(sender=self.user, recipient_email=email).exists():
            raise forms.ValidationError("You have already referred this email address.")
        
        # Check if user with this email already exists and is verified
        try:
            existing_user = User.objects.get(email=email)
            if hasattr(existing_user, 'profile') and existing_user.profile.is_verified:
                raise forms.ValidationError("This user is already verified and doesn't need referrals.")
        except User.DoesNotExist:
            pass  # Email doesn't exist yet, which is fine
        
        return email
    
    def save(self, commit=True):
        referral = super().save(commit=False)
        referral.sender = self.user
        
        # Check if recipient already exists and link them
        try:
            existing_user = User.objects.get(email=referral.recipient_email)
            referral.recipient_user = existing_user
        except User.DoesNotExist:
            pass  # User doesn't exist yet
        
        if commit:
            referral.save()
            
            # Send email notification
            self._send_referral_email(referral)
            
            # If recipient exists, automatically accept the referral
            # (The accept_referral method will handle superadmin auto-verification)
            if referral.recipient_user:
                referral.accept_referral()
        
        return referral
    
    def _send_referral_email(self, referral):
        """Send email notification about the referral"""
        from django.core.mail import send_mail
        from django.conf import settings
        from django.template.loader import render_to_string
        
        try:
            # Get the custom message if provided
            custom_message = self.cleaned_data.get('message', '').strip()
            
            # Email context
            context = {
                'sender_name': referral.sender.first_name or referral.sender.username,
                'recipient_email': referral.recipient_email,
                'custom_message': custom_message,
                'referral_id': referral.id,
            }
            
            # Subject and message
            subject = f"{context['sender_name']} referred you to join GrwCommunity!"
            
            # Plain text message
            message_lines = [
                f"Hi!",
                f"",
                f"{context['sender_name']} has referred you to join GrwCommunity - a platform for professional networking and growth.",
                f"",
            ]
            
            if custom_message:
                message_lines.extend([
                    f"Personal message from {context['sender_name']}:",
                    f'"{custom_message}"',
                    f"",
                ])
            
            message_lines.extend([
                f"GrwCommunity is an invite-only professional networking platform where members connect, share opportunities, and grow their careers together.",
                f"",
                f"To join, you'll need an invite link from {context['sender_name']} or another community member.",
                f"",
                f"Best regards,",
                f"The GrwCommunity Team"
            ])
            
            message = '\n'.join(message_lines)
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@growcommunity.com'),
                recipient_list=[referral.recipient_email],
                fail_silently=True,  # Don't break if email fails
            )
        except Exception as e:
            # Log error but don't break the referral process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send referral email: {e}")


class CustomMessageSlotForm(forms.ModelForm):
    """Form for creating/editing custom message slot categories"""
    
    class Meta:
        model = CustomMessageSlot
        fields = ['name', 'slot_limit', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-2 py-2 text-sm bg-white border border-gray-300 rounded text-black placeholder-gray-400 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors',
                'placeholder': 'Enter category name (e.g., Career Advice)'
            }),
            'slot_limit': forms.NumberInput(attrs={
                'class': 'w-full px-2 py-2 text-sm bg-white border border-gray-300 rounded text-black placeholder-gray-400 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors text-center',
                'min': 0,
                'max': 100,
                'placeholder': '10'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-cyan-600 focus:ring-cyan-500'
            })
        }
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['is_active'].initial = True
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if self.user:
            # Check for duplicate names for this user
            existing = CustomMessageSlot.objects.filter(
                user=self.user,
                name=name
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("You already have a category with this name.")
        return name
    
    def save(self, commit=True):
        slot = super().save(commit=False)
        if self.user:
            slot.user = self.user
        if commit:
            slot.save()
        return slot


class UserMessageSettingsForm(forms.ModelForm):
    """Form for user message settings"""
    
    class Meta:
        model = UserMessageSettings
        fields = ['use_custom_slots']
        widgets = {
            'use_custom_slots': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-cyan-600 focus:ring-cyan-500',
                'onchange': 'toggleSlotMode(this)'
            })
        }
        labels = {
            'use_custom_slots': 'Use custom message categories'
        }
        help_texts = {
            'use_custom_slots': 'Enable to create your own message categories instead of using the default ones'
        }