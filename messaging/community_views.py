from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Conversation, Message
from .forms import MessageRequestForm
from communities.decorators import community_member_required


@community_member_required
def community_inbox(request, community_id, community=None, membership=None):
    """Community-specific inbox showing only conversations with community members"""
    # Use the same method as the regular inbox but filter by community
    from .models import Message, IdentityRevelation, ChatHeading
    
    # Get conversations using the standard method
    all_conversations = Message.get_conversations_for_user(request.user)
    
    # Filter to only include conversations with community members
    conversations = []
    for conversation in all_conversations:
        other_user = conversation['other_user']
        # Check if other user is a member of this community
        if other_user.community_memberships.filter(community=community, is_active=True).exists():
            message_type = conversation.get('message_type')
            # Add identity revelation info
            conversation['identity_revealed'] = IdentityRevelation.has_revealed_identity(other_user, request.user, message_type)
            
            # Get chat heading
            conversation['chat_heading'] = ChatHeading.get_heading_for_chat(request.user, other_user, message_type)
            
            # Determine display name
            if conversation['identity_revealed']:
                conversation['display_name'] = f"{other_user.first_name} {other_user.last_name}" if other_user.first_name else other_user.username
            else:
                conversation['display_name'] = f"User{other_user.id}"
            
            conversations.append(conversation)
    
    context = {
        'conversations': conversations,
        'community': community,
        'community_id': community_id,
        'membership': membership,
    }
    return render(request, 'messaging/inbox.html', context)


@community_member_required
def community_conversation_view(request, community_id, user_id, community=None, membership=None):
    """Redirect to the inbox - conversations are handled there via AJAX"""
    # Simply redirect to the community inbox
    # The inbox.html template handles conversations via JavaScript
    return redirect('messaging:community_inbox', community_id=community_id)


@community_member_required
def community_send_message_request(request, community_id, user_id, community=None, membership=None):
    """Send message request to another user within community context"""
    recipient = get_object_or_404(User, id=user_id)
    
    # Verify the recipient is also a member of this community
    if not recipient.community_memberships.filter(community=community, is_active=True).exists():
        messages.error(request, f'{recipient.username} is not a member of {community.name}.')
        return redirect('communities:user_list', community_id=community_id)
    
    if request.method == 'POST':
        form = MessageRequestForm(request.POST)
        if form.is_valid():
            # Create message request logic here
            subject = form.cleaned_data['subject']
            message_content = form.cleaned_data['message']
            
            # Create message directly
            from .models import Conversation
            
            # Find or create conversation
            conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=recipient
            ).first()
            
            if not conversation:
                conversation = Conversation.objects.create()
                conversation.participants.add(request.user, recipient)
            
            # Create message
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=recipient,
                content=message_content,
                timestamp=timezone.now()
            )
            
            messages.success(request, f'Message sent to {recipient.username}!')
            return redirect('messaging:community_inbox', community_id=community_id)
    else:
        form = MessageRequestForm()
    
    context = {
        'form': form,
        'recipient': recipient,
        'community': community,
        'community_id': community_id,
        'membership': membership,
    }
    return render(request, 'messaging/send_request.html', context)


@require_POST
@community_member_required
def community_send_message_api(request, community_id, community=None, membership=None):
    """API endpoint for sending messages within community context"""
    try:
        data = json.loads(request.body)
        to_user_id = data.get('to_user_id')
        message_content = data.get('message_content', '').strip()
        message_type = data.get('message_type')
        chat_heading = data.get('chat_heading', '').strip()
        
        if not to_user_id:
            return JsonResponse({
                'success': False,
                'error': 'Recipient ID is required'
            }, status=400)
        
        if not message_content:
            return JsonResponse({
                'success': False,
                'error': 'Message content cannot be empty'
            }, status=400)
        
        # Get recipient
        try:
            recipient = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Recipient not found'
            }, status=404)
        
        # Verify the recipient is also a member of this community
        if not recipient.community_memberships.filter(community=community, is_active=True).exists():
            return JsonResponse({
                'success': False,
                'error': f'{recipient.username} is not a member of {community.name}.'
            }, status=403)
        
        # Get or create conversation
        from .models import Conversation
        
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=recipient
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, recipient)
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            receiver=recipient,
            content=message_content,
            timestamp=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Message sent to {recipient.username}!',
            'conversation_url': f'/messages/community/{community_id}/conversation/{recipient.id}/'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


