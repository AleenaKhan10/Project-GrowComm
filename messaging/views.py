from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Max, Count, OuterRef, Subquery, Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.utils import timezone
import json

from .models import (
    Conversation, Message, MessageRequest, 
    MessageType, UserMessageSettings, MessageSlotBooking
)
from .forms import MessageRequestForm, MessageReplyForm, UserMessageSettingsForm
from profiles.decorators import verified_user_required


@login_required
def inbox(request):
    """
    Display user's message inbox with grouped conversations.
    Groups messages by sender/receiver and shows latest message from each conversation.
    """
    # Get conversations using the optimized method
    conversations = Message.get_conversations_for_user(request.user)
    
    # Get pending message requests
    pending_requests = MessageRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user', 'from_user__profile', 'message_type').order_by('-created_date')
    
    # Count total unread messages
    total_unread = Message.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()
    
    context = {
        'conversations': conversations,
        'pending_requests': pending_requests,
        'total_unread': total_unread,
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
def conversation_view(request, user_id):
    """
    View conversation with a specific user.
    Shows all messages between the logged-in user and the specified user.
    """
    other_user = get_object_or_404(User, id=user_id)
    
    if other_user == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect('messaging:inbox')
    
    # Get messages between these two users
    message_list = Message.get_messages_between_users(request.user, other_user, limit=100)
    
    # Mark messages as read
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True, read_date=timezone.now())
    
    # Handle message sending via POST (check verification)
    if request.method == 'POST':
        # Check if user is verified before allowing message sending (superadmins bypass)
        if not request.user.is_superuser and not request.user.profile.is_verified:
            messages.warning(request, f"You need {request.user.profile.referrals_needed} more referrals to send messages.")
            return redirect('profiles:referrals')
        
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content
            )
            messages.success(request, 'Message sent successfully!')
            return redirect('messaging:conversation', user_id=user_id)
        else:
            messages.error(request, 'Message content cannot be empty.')
    
    # Get user's profile for display
    try:
        other_user_profile = other_user.profile
    except:
        other_user_profile = None
    
    context = {
        'other_user': other_user,
        'other_user_profile': other_user_profile,
        'messages': message_list,
        'conversation_messages': message_list,  # Alias for template compatibility
    }
    return render(request, 'messaging/conversation.html', context)


@login_required
@verified_user_required
@require_http_methods(["POST"])
def send_message(request):
    """
    AJAX endpoint to send a message.
    Expects JSON with receiver_id, content, and optionally message_type_id.
    """
    try:
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        content = data.get('content', '').strip()
        message_type_id = data.get('message_type_id')
        
        if not receiver_id:
            return JsonResponse({
                'success': False,
                'error': 'Receiver ID is required'
            }, status=400)
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Message content cannot be empty'
            }, status=400)
        
        # Get receiver
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Receiver not found'
            }, status=404)
        
        # Don't allow messaging yourself
        if receiver == request.user:
            return JsonResponse({
                'success': False,
                'error': 'You cannot message yourself'
            }, status=400)
        
        # Get message type if provided
        message_type = None
        if message_type_id:
            try:
                message_type = MessageType.objects.get(id=message_type_id)
            except MessageType.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid message type'
                }, status=400)
            
            # Check slot availability if message type is provided
            can_send, reason = MessageSlotBooking.can_user_send_message(request.user, receiver, message_type)
            if not can_send:
                error_messages = {
                    'already_sent': f'You have already sent a {message_type.name} message to {receiver.username}. Please wait 3 days before sending another.',
                    'slots_full': f'{receiver.username}\'s {message_type.name} slots are currently full. Please try again later.'
                }
                return JsonResponse({
                    'success': False,
                    'error': error_messages.get(reason, 'Cannot send message at this time')
                }, status=400)
        
        # Create the message
        message = Message.objects.create(
            sender=request.user,
            receiver=receiver,
            content=content,
            message_type=message_type
        )
        
        # Book slot if message type is provided
        if message_type:
            booking, booking_reason = MessageSlotBooking.book_slot(
                request.user, receiver, message_type, message
            )
            if not booking:
                # If booking failed, delete the message and return error
                message.delete()
                return JsonResponse({
                    'success': False,
                    'error': f'Failed to send message: {booking_reason}'
                }, status=400)
        
        # Return success with message data
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender.id,
                'sender_name': message.sender.username,
                'timestamp': message.timestamp.isoformat(),
                'is_read': message.is_read,
                'message_type': {
                    'id': message_type.id,
                    'name': message_type.name
                } if message_type else None
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_messages(request, user_id):
    """
    AJAX endpoint to get messages between logged-in user and specified user.
    Returns messages in JSON format. Can filter by message_type_id parameter.
    """
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    # Get message type filter if provided
    message_type_id = request.GET.get('message_type_id')
    message_type = None
    filter_by_message_type = False
    
    if message_type_id is not None:  # Parameter was provided
        filter_by_message_type = True
        if message_type_id and message_type_id != 'null':  # Has actual value
            try:
                message_type = MessageType.objects.get(id=message_type_id)
            except MessageType.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Message type not found'
                }, status=404)
        # else: message_type remains None (for null/general messages)
    
    # Get messages with message type filtering
    if filter_by_message_type:
        # Filter by specific message type (including None for general messages)
        message_filter = Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
        if message_type:
            message_filter &= Q(message_type=message_type)
        else:
            message_filter &= Q(message_type__isnull=True)
        
        messages_list = Message.objects.filter(message_filter).order_by('-timestamp')[:100]
        messages_list = list(reversed(messages_list))  # Chronological order
    else:
        # No filtering - get all messages (fallback)
        messages_list = Message.get_messages_between_users(
            request.user, other_user, limit=100
        )
    
    # Mark messages as read (with message type filter)
    mark_read_filter = Q(sender=other_user, receiver=request.user, is_read=False)
    if filter_by_message_type:
        if message_type:
            mark_read_filter &= Q(message_type=message_type)
        else:
            mark_read_filter &= Q(message_type__isnull=True)
    
    Message.objects.filter(mark_read_filter).update(is_read=True, read_date=timezone.now())
    
    # Format messages for JSON response
    messages_data = []
    for msg in messages_list:
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'sender_id': msg.sender.id,
            'sender_name': msg.sender.username,
            'receiver_id': msg.receiver.id,
            'receiver_name': msg.receiver.username,
            'timestamp': msg.timestamp.isoformat(),
            'is_read': msg.is_read,
            'is_mine': msg.sender == request.user,
            'message_type': {
                'id': msg.message_type.id,
                'name': msg.message_type.name
            } if msg.message_type else None
        })
    
    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'other_user': {
            'id': other_user.id,
            'username': other_user.username,
            'display_name': getattr(other_user.profile, 'display_name', other_user.username) if hasattr(other_user, 'profile') else other_user.username
        },
        'message_type': {
            'id': message_type.id,
            'name': message_type.name
        } if message_type else None
    })


@login_required
def mark_as_read(request, message_id):
    """
    AJAX endpoint to mark a specific message as read.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)
    
    try:
        message = Message.objects.get(id=message_id, receiver=request.user)
        message.mark_as_read()
        return JsonResponse({'success': True})
    except Message.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Message not found or access denied'
        }, status=404)


@login_required
def conversation_detail(request, conversation_id):
    """
    Legacy view for backward compatibility with existing conversation URLs.
    Redirects to the new conversation view.
    """
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    # Get the other participant
    other_user = conversation.participants.exclude(id=request.user.id).first()
    
    if other_user:
        return redirect('messaging:conversation', user_id=other_user.id)
    else:
        messages.error(request, "Invalid conversation.")
        return redirect('messaging:inbox')


@login_required
@verified_user_required
def send_message_request(request, user_id):
    """Send a message request to another user with slot availability checking"""
    recipient = get_object_or_404(User, id=user_id)
    
    if recipient == request.user:
        messages.error(request, "You cannot send a message to yourself.")
        return redirect('communities:user_list')
    
    # Get slot availability information for this recipient
    try:
        recipient_message_settings = recipient.message_settings
        slot_availability = recipient_message_settings.get_slot_availability_for_user(request.user)
    except:
        slot_availability = {}
    
    # Get all active message types
    message_types = MessageType.objects.filter(is_active=True)
    
    if request.method == 'POST':
        message_type_id = request.POST.get('message_type')
        initial_message = request.POST.get('initial_message', '').strip()
        
        if not message_type_id:
            messages.error(request, "Please select a message type.")
            return render(request, 'messaging/send_request.html', {
                'recipient': recipient,
                'message_types': message_types,
                'slot_availability': slot_availability,
            })
        
        if not initial_message:
            messages.error(request, "Please enter an initial message.")
            return render(request, 'messaging/send_request.html', {
                'recipient': recipient,
                'message_types': message_types,
                'slot_availability': slot_availability,
            })
        
        try:
            message_type = MessageType.objects.get(id=message_type_id)
        except MessageType.DoesNotExist:
            messages.error(request, "Invalid message type selected.")
            return render(request, 'messaging/send_request.html', {
                'recipient': recipient,
                'message_types': message_types,
                'slot_availability': slot_availability,
            })
        
        # Check slot availability before creating message
        can_send, reason = MessageSlotBooking.can_user_send_message(request.user, recipient, message_type)
        
        if not can_send:
            if reason == "already_sent":
                messages.error(request, f"You have already sent a {message_type.name} message to {recipient.username}. Please wait 3 days before sending another.")
            elif reason == "slots_full":
                messages.error(request, f"{recipient.username}'s {message_type.name} slots are currently full. Please try again later.")
            return render(request, 'messaging/send_request.html', {
                'recipient': recipient,
                'message_types': message_types,
                'slot_availability': slot_availability,
            })
        
        # Create the message directly (no request system for slot-based messages)
        message = Message.objects.create(
            sender=request.user,
            receiver=recipient,
            content=initial_message,
            message_type=message_type
        )
        
        # Book the slot
        booking, booking_reason = MessageSlotBooking.book_slot(
            request.user, recipient, message_type, message
        )
        
        if booking:
            messages.success(request, f'{message_type.name} message sent to {recipient.username}!')
            return redirect('messaging:conversation', user_id=recipient.id)
        else:
            # If booking failed, delete the message
            message.delete()
            messages.error(request, f'Failed to send message: {booking_reason}')
    
    context = {
        'recipient': recipient,
        'message_types': message_types,
        'slot_availability': slot_availability,
    }
    return render(request, 'messaging/send_request.html', context)


@login_required
def message_requests(request):
    """View and manage incoming message requests"""
    pending_requests = MessageRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user', 'from_user__profile', 'message_type').order_by('-created_date')
    
    responded_requests = MessageRequest.objects.filter(
        to_user=request.user,
        status__in=['accepted', 'declined']
    ).select_related('from_user', 'from_user__profile', 'message_type').order_by('-responded_date')[:10]
    
    context = {
        'pending_requests': pending_requests,
        'responded_requests': responded_requests,
    }
    return render(request, 'messaging/message_requests.html', context)


@login_required
@require_POST
def respond_to_request(request, request_id):
    """Accept or decline a message request"""
    message_request = get_object_or_404(
        MessageRequest,
        id=request_id,
        to_user=request.user,
        status='pending'
    )
    
    action = request.POST.get('action')
    
    if action == 'accept':
        conversation = message_request.accept()
        messages.success(request, f'Message request from {message_request.from_user.username} accepted!')
        # Redirect to conversation with the user
        return redirect('messaging:conversation', user_id=message_request.from_user.id)
    elif action == 'decline':
        message_request.decline()
        messages.success(request, f'Message request from {message_request.from_user.username} declined.')
    
    return redirect('messaging:message_requests')


@login_required
def message_settings(request):
    """Edit user's message settings"""
    settings, created = UserMessageSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserMessageSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your message settings have been updated!')
            return redirect('messaging:settings')
    else:
        form = UserMessageSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'settings': settings,
    }
    return render(request, 'messaging/settings.html', context)


@login_required
def sent_requests(request):
    """View sent message requests"""
    sent_requests = MessageRequest.objects.filter(
        from_user=request.user
    ).select_related('to_user', 'to_user__profile', 'message_type').order_by('-created_date')
    
    context = {
        'sent_requests': sent_requests,
    }
    return render(request, 'messaging/sent_requests.html', context)


@login_required
def get_conversation_messages(request, conversation_id):
    """
    Legacy API endpoint for backward compatibility.
    Gets messages for a conversation.
    """
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    # Get the other participant
    other_user = conversation.participants.exclude(id=request.user.id).first()
    
    if not other_user:
        return JsonResponse({
            'success': False,
            'error': 'Invalid conversation'
        }, status=400)
    
    # Redirect to new endpoint
    return get_messages(request, other_user.id)


@login_required
@require_http_methods(["POST"])
def send_conversation_reply(request, conversation_id):
    """
    Legacy API endpoint for backward compatibility.
    Sends a reply to a conversation.
    """
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Message content is required'
            }, status=400)
        
        # Get the recipient (other participant)
        recipient = conversation.participants.exclude(id=request.user.id).first()
        
        if not recipient:
            return JsonResponse({
                'success': False,
                'error': 'Invalid conversation'
            }, status=400)
        
        # Create the message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            receiver=recipient,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender.id,
                'timestamp': message.timestamp.isoformat(),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def search_users(request):
    """
    AJAX endpoint to search for users to message.
    Returns users matching the search query.
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({
            'success': False,
            'error': 'Search query must be at least 2 characters'
        }, status=400)
    
    # Search users by username, first name, or last name
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).select_related('profile')[:20]
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'display_name': getattr(user.profile, 'display_name', user.username) if hasattr(user, 'profile') else user.username,
            'avatar_url': getattr(user.profile, 'avatar_url', None) if hasattr(user, 'profile') else None
        })
    
    return JsonResponse({
        'success': True,
        'users': users_data
    })


@login_required
def unread_count(request):
    """
    AJAX endpoint to get the count of unread messages.
    """
    count = Message.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'success': True,
        'unread_count': count
    })