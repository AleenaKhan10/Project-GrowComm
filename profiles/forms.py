from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    
    # User fields
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
            'placeholder': 'Enter your last name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
            'placeholder': 'Enter your email address'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'bio', 'company', 'team', 'organization_level',
            'schools', 'tags', 'phone_number', 'name_visibility',
            'coffee_chat_slots', 'mentorship_slots', 'networking_slots', 'general_slots'
        ]
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-300 file:mr-4 file:py-3 file:px-4 file:rounded file:border file:border-gray-600 file:text-sm file:font-medium file:bg-gray-800 file:text-white hover:file:bg-gray-700 transition-colors',
                'accept': 'image/*'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors min-h-[100px]',
                'rows': 4,
                'placeholder': 'Tell us about yourself, your interests, and what you bring to the community...'
            }),
            'company': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'placeholder': 'Your current company or organization'
            }),
            'team': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'placeholder': 'Your team or department'
            }),
            'organization_level': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors'
            }),
            'schools': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'placeholder': 'Universities, schools, or educational institutions'
            }),
            'tags': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors min-h-[100px]',
                'rows': 3,
                'placeholder': 'Enter skills, interests, or expertise areas (comma-separated)\nExample: Python, Data Science, Startup, Machine Learning, Product Management'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'placeholder': 'Your phone number (optional)'
            }),
            'name_visibility': forms.Select(attrs={
                'class': 'w-3/5 px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors'
            }),
            'coffee_chat_slots': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'min': 0,
                'max': 50,
                'placeholder': '5'
            }),
            'mentorship_slots': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'min': 0,
                'max': 20,
                'placeholder': '2'
            }),
            'networking_slots': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'min': 0,
                'max': 100,
                'placeholder': '10'
            }),
            'general_slots': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-400 focus:ring-2 focus:ring-lime-400 focus:border-lime-400 transition-colors',
                'min': 0,
                'max': 100,
                'placeholder': '15'
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
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Search by name, company, skills, or interests...'
        })
    )
    organization_level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Levels')] + UserProfile.ORGANIZATION_LEVELS,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
        })
    )
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Filter by tags...'
        })
    )