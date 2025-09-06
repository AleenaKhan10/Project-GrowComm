from django import forms
from django.forms import modelformset_factory
from .models import MessageRequest, MessageType, UserMessageSettings, CustomMessageSlot


class MessageRequestForm(forms.ModelForm):
    """Form for sending a message request"""
    
    class Meta:
        model = MessageRequest
        fields = ['message_type', 'initial_message']
        widgets = {
            'message_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'initial_message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'rows': 5,
                'placeholder': 'Write your initial message here. Be clear about what you\'re looking for and why you\'d like to connect...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active message types
        self.fields['message_type'].queryset = MessageType.objects.filter(is_active=True)


class MessageReplyForm(forms.Form):
    """Form for replying to messages in a conversation"""
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-none',
            'rows': 3,
            'placeholder': 'Type your message...'
        })
    )


class UserMessageSettingsForm(forms.ModelForm):
    """Form for editing user message settings"""
    
    class Meta:
        model = UserMessageSettings
        fields = [
            'use_custom_slots',
            'coffee_chat_enabled', 'mentorship_enabled', 'networking_enabled', 'general_enabled',
            'auto_accept_from_moderators', 'auto_accept_from_admins', 'email_notifications'
        ]
        widgets = {
            'use_custom_slots': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded',
                'onchange': 'toggleSlotMode(this)'
            }),
            'coffee_chat_enabled': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            }),
            'mentorship_enabled': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            }),
            'networking_enabled': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            }),
            'general_enabled': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            }),
            'auto_accept_from_moderators': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            }),
            'auto_accept_from_admins': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            }),
        }
        
        labels = {
            'use_custom_slots': 'Use Custom Message Categories',
            'coffee_chat_enabled': 'Accept Coffee Chat requests',
            'mentorship_enabled': 'Accept Mentorship requests',
            'networking_enabled': 'Accept Networking requests',
            'general_enabled': 'Accept General message requests',
            'auto_accept_from_moderators': 'Auto-accept requests from community moderators',
            'auto_accept_from_admins': 'Auto-accept requests from community admins',
            'email_notifications': 'Receive email notifications for new messages',
        }


class CustomMessageSlotForm(forms.ModelForm):
    """Form for creating/editing custom message slots"""
    
    class Meta:
        model = CustomMessageSlot
        fields = ['name', 'slot_limit', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'e.g., Quick Question, Project Discussion'
            }),
            'slot_limit': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'min': '0',
                'max': '100'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded'
            })
        }
        labels = {
            'name': 'Category Name',
            'slot_limit': 'Slot Limit (per 3 days)',
            'is_active': 'Active'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if self.user and name:
            existing = CustomMessageSlot.objects.filter(
                user=self.user,
                name__iexact=name
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(f"You already have a category named '{name}'")
        return name


# Formset for managing multiple custom slots
CustomMessageSlotFormSet = modelformset_factory(
    CustomMessageSlot,
    form=CustomMessageSlotForm,
    extra=1,
    can_delete=True,
    max_num=20,
    validate_max=True
)