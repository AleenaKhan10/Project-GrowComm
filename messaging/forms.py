from django import forms
from .models import MessageRequest, MessageType, UserMessageSettings


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
            'coffee_chat_enabled', 'mentorship_enabled', 'networking_enabled', 'general_enabled',
            'auto_accept_from_moderators', 'auto_accept_from_admins', 'email_notifications'
        ]
        widgets = {
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
            'coffee_chat_enabled': 'Accept Coffee Chat requests',
            'mentorship_enabled': 'Accept Mentorship requests',
            'networking_enabled': 'Accept Networking requests',
            'general_enabled': 'Accept General message requests',
            'auto_accept_from_moderators': 'Auto-accept requests from community moderators',
            'auto_accept_from_admins': 'Auto-accept requests from community admins',
            'email_notifications': 'Receive email notifications for new messages',
        }