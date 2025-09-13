from django import forms
from datetime import datetime, timedelta
from .models import InviteLink


class CreateInviteForm(forms.ModelForm):
    """Form for creating new invite links"""
    
    expires_in_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=7,
        help_text="Number of days until the invite expires (1-30 days)",
        widget=forms.NumberInput(attrs={
            'class': 'input',
            'placeholder': 'Enter number of days (1-30)',
        })
    )
    
    class Meta:
        model = InviteLink
        fields = []  # We don't include model fields directly
    
    def save(self, user, commit=True):
        """Create invite link with expiry date and link to user's community"""
        expires_in_days = self.cleaned_data['expires_in_days']
        expiry_date = datetime.now() + timedelta(days=expires_in_days)
        
        # Get user's community (if they have one)
        community = None
        if hasattr(user, 'community_memberships'):
            membership = user.community_memberships.filter(is_active=True).first()
            if membership:
                community = membership.community
        
        invite = InviteLink.objects.create(
            created_by=user,
            community=community,
            expiry_date=expiry_date
        )
        return invite