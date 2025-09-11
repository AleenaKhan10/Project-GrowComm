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
    MessageType, UserMessageSettings, MessageSlotBooking, IdentityRevelation,
    CustomMessageSlot, MessageReport, UserBlock, ChatBlock, ChatHeading
)
from .forms import (
    MessageRequestForm, MessageReplyForm, UserMessageSettingsForm,
    CustomMessageSlotForm, CustomMessageSlotFormSet
)
from profiles.decorators import verified_user_required
from audittrack.utils import log_slot_booked, log_message_answered


@login_required
def inbox(request):
    """
    Display user's message inbox with grouped conversations.
    Groups messages by sender/receiver and shows latest message from each conversation.
    """
    # Get conversations using the optimized method
    conversations = Message.get_conversations_for_user(request.user)
    
    # Enhance conversations with identity revelation info and chat headings
    for conversation in conversations:
        other_user = conversation['other_user']
        message_type = conversation.get('message_type')
        # Check if other user revealed their identity to current user for this message type
        conversation['identity_revealed'] = IdentityRevelation.has_revealed_identity(other_user, request.user, message_type)
        
        # Get chat heading set by current user for this conversation
        conversation['chat_heading'] = ChatHeading.get_heading_for_chat(request.user, other_user, message_type)
        
        # Determine display name for inbox based on identity revelation
        if conversation['identity_revealed']:
            # Identity revealed - show their real name (first + last name)
            conversation['display_name'] = other_user.profile.real_name if hasattr(other_user, 'profile') else other_user.username
        else:
            # Identity not revealed - show anonymous name only if they chose anonymous visibility
            if hasattr(other_user, 'profile') and other_user.profile.name_visibility == 'anonymous':
                conversation['display_name'] = "Anonymous Member"
            else:
                # For non-anonymous users, show their chosen display name
                conversation['display_name'] = other_user.profile.display_name if hasattr(other_user, 'profile') else other_user.username
    
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
    
    # Handle message sending via POST
    if request.method == 'POST':
        # Check if there's an existing conversation between these users and get its message_type
        existing_message = Message.objects.filter(
            (Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user))
        ).first()
        
        # Get the message_type from existing conversation if it exists
        existing_message_type = existing_message.message_type if existing_message else None
        
        # Only require verification for NEW conversations, not for replies in existing conversations
        if not existing_message:
            if not request.user.is_superuser and not request.user.profile.is_verified:
                messages.warning(request, f"You need {request.user.profile.referrals_needed} more referrals to start new conversations.")
                return redirect('profiles:referrals')
        
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content,
                message_type=existing_message_type  # Preserve the message_type from the conversation
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
@require_http_methods(["POST"])
def send_message(request):
    """
    AJAX endpoint to send a message.
    Expects JSON with receiver_id, content, and optionally message_type_id.
    
    For NEW conversations: Requires verification and respects slot limits
    For EXISTING conversations: No verification required, no slot limits
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
        
        # Check if chat is blocked between users
        from .models import ChatBlock
        if ChatBlock.is_chat_blocked(request.user, receiver):
            return JsonResponse({
                'success': False,
                'error': 'This chat is currently blocked due to a report. Please contact administrators.'
            }, status=403)
        
        # Check if there's an existing conversation between these users FOR THE SAME MESSAGE TYPE
        # Different message types should create separate conversations
        message_type = None
        if message_type_id:
            try:
                message_type = MessageType.objects.get(id=message_type_id)
            except MessageType.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid message type'
                }, status=400)
        
        # Check for existing conversation with the SAME message type (or both None)
        existing_conversation = Message.objects.filter(
            (Q(sender=request.user, receiver=receiver) | Q(sender=receiver, receiver=request.user)),
            message_type=message_type  # SAME message type only
        ).first()
        
        # For NEW conversations, apply slot restrictions and verification
        if not existing_conversation:
            # Check if user is suspended
            if not request.user.is_superuser and request.user.profile.is_suspended:
                return JsonResponse({
                    'success': False,
                    'error': 'You cannot perform this action. Your account is suspended.'
                }, status=403)
            
            # Check verification for new conversations
            if not request.user.is_superuser and not request.user.profile.is_verified:
                return JsonResponse({
                    'success': False,
                    'error': f'You need {request.user.profile.referrals_needed} more referrals to start new conversations.'
                }, status=403)
            
            # Check slot availability for new conversations with message type
            if message_type:
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
            
            # Create the message for new conversation
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
                else:
                    # Log slot booking
                    log_slot_booked(request.user, f"Booked {message_type.name} slot with {receiver.username}")
        else:
            # For EXISTING conversations with same message type, check suspension status
            # Check if user is suspended
            if not request.user.is_superuser and request.user.profile.is_suspended:
                return JsonResponse({
                    'success': False,
                    'error': 'You cannot perform this action. Your account is suspended.'
                }, status=403)
            
            # Check if this is the first time the receiver is responding to the sender
            is_first_response = not Message.objects.filter(
                sender=request.user,
                receiver=receiver,
                message_type=message_type
            ).exists()
            
            # Use the same message_type to keep messages in the same conversation
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content,
                message_type=message_type  # Use the message type from the request (same as existing)
            )
            
            # Log first time message answer
            if is_first_response:
                log_message_answered(request.user, f"First response to {receiver.username} in {message_type.name if message_type else 'general'} conversation")
        
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
                    'id': message.message_type.id,
                    'name': message.message_type.name
                } if message.message_type else None
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
    
    # Check if chat is blocked between users
    from .models import ChatBlock
    if ChatBlock.is_chat_blocked(request.user, other_user):
        return JsonResponse({
            'success': False,
            'error': 'This chat is currently blocked due to a report.',
            'blocked': True
        }, status=403)
    
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
        # Determine display name based on identity revelation and user preferences
        if msg.sender == request.user:
            # Current user's message - always show their chosen display name
            sender_display_name = msg.sender.profile.display_name if hasattr(msg.sender, 'profile') else msg.sender.username
        else:
            # Other user's message - check identity revelation and user preferences
            if IdentityRevelation.has_revealed_identity(msg.sender, request.user, msg.message_type):
                # Identity revealed - show their real name (first + last name)
                sender_display_name = msg.sender.profile.real_name if hasattr(msg.sender, 'profile') else msg.sender.username
            else:
                # Identity not revealed - check user's visibility preference
                if hasattr(msg.sender, 'profile') and msg.sender.profile.name_visibility == 'anonymous':
                    # User chose to be anonymous - show "Anonymous Member"
                    sender_display_name = "Anonymous Member"
                else:
                    # User didn't choose anonymous - show their chosen display name
                    sender_display_name = msg.sender.profile.display_name if hasattr(msg.sender, 'profile') else msg.sender.username
        
        # For receiver display name (in case needed)
        if msg.receiver == request.user:
            receiver_display_name = msg.receiver.profile.display_name if hasattr(msg.receiver, 'profile') else msg.receiver.username
        else:
            # Other user as receiver - check identity revelation and user preferences
            if IdentityRevelation.has_revealed_identity(msg.receiver, request.user, msg.message_type):
                # Identity revealed - show their real name (first + last name)
                receiver_display_name = msg.receiver.profile.real_name if hasattr(msg.receiver, 'profile') else msg.receiver.username
            else:
                # Identity not revealed - check user's visibility preference
                if hasattr(msg.receiver, 'profile') and msg.receiver.profile.name_visibility == 'anonymous':
                    # User chose to be anonymous - show "Anonymous Member"
                    receiver_display_name = "Anonymous Member"
                else:
                    # User didn't choose anonymous - show their chosen display name
                    receiver_display_name = msg.receiver.profile.display_name if hasattr(msg.receiver, 'profile') else msg.receiver.username
        
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'sender_id': msg.sender.id,
            'sender_name': sender_display_name,
            'receiver_id': msg.receiver.id,
            'receiver_name': receiver_display_name,
            'timestamp': msg.timestamp.isoformat(),
            'is_read': msg.is_read,
            'is_mine': msg.sender == request.user,
            'message_type': {
                'id': msg.message_type.id,
                'name': msg.message_type.name
            } if msg.message_type else None
        })
    
    # Determine other user's display name based on identity revelation and user preferences
    # Need to determine the message_type for this conversation
    if filter_by_message_type and message_type:
        check_message_type = message_type
    else:
        check_message_type = None
    
    if IdentityRevelation.has_revealed_identity(other_user, request.user, check_message_type):
        # Identity revealed - show their real name (first + last name)
        other_user_display_name = other_user.profile.real_name if hasattr(other_user, 'profile') else other_user.username
        identity_revealed = True
    else:
        # Identity not revealed - check user's visibility preference
        if hasattr(other_user, 'profile') and other_user.profile.name_visibility == 'anonymous':
            # User chose to be anonymous - show "Anonymous Member"
            other_user_display_name = "Anonymous Member"
        else:
            # User didn't choose anonymous - show their chosen display name
            other_user_display_name = other_user.profile.display_name if hasattr(other_user, 'profile') else other_user.username
        identity_revealed = False
    
    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'other_user': {
            'id': other_user.id,
            'username': other_user.username,
            'display_name': other_user_display_name,
            'identity_revealed': identity_revealed
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
            # Log slot booking
            log_slot_booked(request.user, f"Booked {message_type.name} slot with {recipient.username}")
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
    """Edit user's message settings and manage custom message categories"""
    settings, created = UserMessageSettings.objects.get_or_create(user=request.user)
    
    # Get existing custom slots for the user
    custom_slots = CustomMessageSlot.objects.filter(user=request.user)
    
    if request.method == 'POST':
        # Handle main settings form
        if 'save_settings' in request.POST:
            form = UserMessageSettingsForm(request.POST, instance=settings)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your message settings have been updated!')
                return redirect('messaging:settings')
        
        # Handle adding new custom slot
        elif 'add_slot' in request.POST:
            slot_form = CustomMessageSlotForm(request.POST, user=request.user)
            if slot_form.is_valid():
                slot = slot_form.save(commit=False)
                slot.user = request.user
                slot.save()
                messages.success(request, f'Custom category "{slot.name}" has been added!')
                return redirect('messaging:settings')
        
        # Handle editing existing slot
        elif 'edit_slot' in request.POST:
            slot_id = request.POST.get('slot_id')
            slot = get_object_or_404(CustomMessageSlot, id=slot_id, user=request.user)
            slot_form = CustomMessageSlotForm(request.POST, instance=slot, user=request.user)
            if slot_form.is_valid():
                slot_form.save()
                messages.success(request, 'Custom category has been updated!')
                return redirect('messaging:settings')
        
        # Handle deleting slot
        elif 'delete_slot' in request.POST:
            slot_id = request.POST.get('slot_id')
            slot = get_object_or_404(CustomMessageSlot, id=slot_id, user=request.user)
            slot_name = slot.name
            slot.delete()
            messages.success(request, f'Custom category "{slot_name}" has been deleted!')
            return redirect('messaging:settings')
        
        else:
            form = UserMessageSettingsForm(instance=settings)
            slot_form = CustomMessageSlotForm(user=request.user)
    else:
        form = UserMessageSettingsForm(instance=settings)
        slot_form = CustomMessageSlotForm(user=request.user)
    
    context = {
        'form': form,
        'settings': settings,
        'slot_form': slot_form,
        'custom_slots': custom_slots,
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


@login_required
@require_POST
def reveal_identity(request, user_id):
    """
    AJAX endpoint for user to reveal their identity to another user for a specific message type.
    """
    try:
        # Get the user to reveal identity to
        revealed_to_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    if revealed_to_user == request.user:
        return JsonResponse({
            'success': False,
            'error': 'You cannot reveal identity to yourself'
        }, status=400)
    
    # Get message_type_id from request body
    try:
        import json
        body = json.loads(request.body) if request.body else {}
        message_type_id = body.get('message_type_id')
    except:
        message_type_id = None
    
    # Get message type if provided
    message_type = None
    if message_type_id:
        try:
            message_type = MessageType.objects.get(id=message_type_id)
        except MessageType.DoesNotExist:
            pass
    
    # Check if there are any messages between these users for this message type
    message_filter = Q(sender=request.user, receiver=revealed_to_user) | Q(sender=revealed_to_user, receiver=request.user)
    if message_type:
        message_filter &= Q(message_type=message_type)
    else:
        message_filter &= Q(message_type__isnull=True)
    
    messages_exist = Message.objects.filter(message_filter).exists()
    
    if not messages_exist:
        return JsonResponse({
            'success': False,
            'error': 'No conversation exists with this user for this message type'
        }, status=400)
    
    # Reveal identity for specific message type
    revelation, created = IdentityRevelation.reveal_identity(request.user, revealed_to_user, message_type)
    
    return JsonResponse({
        'success': True,
        'message': 'Your identity has been revealed!' if created else 'Identity was already revealed.',
        'already_revealed': not created,
        'revealed_name': request.user.profile.display_name if hasattr(request.user, 'profile') else request.user.username
    })


@login_required
@require_POST
def report_user(request, user_id):
    """Report a user from conversation"""
    try:
        reported_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    
    if reported_user == request.user:
        return JsonResponse({'success': False, 'error': 'You cannot report yourself'}, status=400)
    
    # Parse request data
    try:
        data = json.loads(request.body)
        report_type = data.get('report_type')
        note = data.get('note', '')
    except:
        report_type = request.POST.get('report_type')
        note = request.POST.get('note', '')
    
    # Validate report type
    valid_types = [choice[0] for choice in MessageReport.REPORT_TYPES]
    if report_type not in valid_types:
        return JsonResponse({'success': False, 'error': 'Invalid report type'}, status=400)
    
    # Create report
    report = MessageReport.objects.create(
        reporter=request.user,
        reported_user=reported_user,
        report_type=report_type,
        note=note
    )
    
    # Create chat block
    from .models import ChatBlock
    chat_block, created = ChatBlock.objects.get_or_create(
        reporter=request.user,
        blocked_user=reported_user,
        defaults={
            'report': report,
            'chat_id': f"{min(request.user.id, reported_user.id)}_{max(request.user.id, reported_user.id)}",
            'is_active': True,
            'reviewed_by_admin': False
        }
    )
    
    if not created:
        # Update existing block to reference this report
        chat_block.report = report
        chat_block.is_active = True
        chat_block.save()
    
    messages.success(request, f'User {reported_user.username} has been reported and blocked. Administrators will review your report.')
    
    return JsonResponse({
        'success': True,
        'message': 'Report submitted and user blocked successfully'
    })


@login_required
@require_POST
def block_user(request, user_id):
    """Block/unblock a user"""
    try:
        user_to_block = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    
    if user_to_block == request.user:
        return JsonResponse({'success': False, 'error': 'You cannot block yourself'}, status=400)
    
    # Check if already blocked
    existing_block = UserBlock.objects.filter(blocker=request.user, blocked=user_to_block).first()
    
    if existing_block:
        # Unblock
        existing_block.delete()
        messages.success(request, f'User {user_to_block.username} has been unblocked.')
        return JsonResponse({
            'success': True,
            'message': 'User unblocked',
            'blocked': False
        })
    else:
        # Block
        UserBlock.objects.create(
            blocker=request.user,
            blocked=user_to_block
        )
        messages.success(request, f'User {user_to_block.username} has been blocked.')
        return JsonResponse({
            'success': True,
            'message': 'User blocked',
            'blocked': True
        })


@login_required
def blocked_users(request):
    """View list of blocked users"""
    blocks = UserBlock.objects.filter(blocker=request.user).select_related('blocked')
    
    context = {
        'blocked_users': blocks
    }
    return render(request, 'messaging/blocked_users.html', context)


# ============================================================================
# ADMIN VIEWS FOR REPORTS AND CHAT BLOCKS MANAGEMENT
# ============================================================================

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count


@staff_member_required
def admin_dashboard(request):
    """Dashboard showing report statistics"""
    # Get report statistics
    report_stats = {
        'total_reports': MessageReport.objects.count(),
        'pending_reports': MessageReport.objects.filter(
            chat_blocks__reviewed_by_admin=False
        ).count(),
        'reviewed_reports': MessageReport.objects.filter(
            chat_blocks__reviewed_by_admin=True
        ).count(),
    }
    
    # Get report type distribution
    report_type_stats = MessageReport.objects.values('report_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get chat block statistics
    chat_block_stats = {
        'total_blocks': ChatBlock.objects.count(),
        'active_blocks': ChatBlock.objects.filter(is_active=True).count(),
        'inactive_blocks': ChatBlock.objects.filter(is_active=False).count(),
        'unreviewed_blocks': ChatBlock.objects.filter(reviewed_by_admin=False).count(),
    }
    
    # Recent reports (last 10)
    recent_reports = MessageReport.objects.select_related(
        'reporter', 'reported_user'
    ).order_by('-created_date')[:10]
    
    # Recent chat blocks (last 10)
    recent_blocks = ChatBlock.objects.select_related(
        'reporter', 'blocked_user', 'report'
    ).order_by('-created_date')[:10]
    
    context = {
        'report_stats': report_stats,
        'report_type_stats': report_type_stats,
        'chat_block_stats': chat_block_stats,
        'recent_reports': recent_reports,
        'recent_blocks': recent_blocks,
    }
    return render(request, 'messaging/admin/dashboard.html', context)


@staff_member_required
def admin_reports_list(request):
    """List all reports with filtering and search"""
    reports = MessageReport.objects.select_related(
        'reporter', 'reported_user'
    ).prefetch_related('chat_blocks')
    
    # Filter by report type
    report_type = request.GET.get('report_type')
    if report_type:
        reports = reports.filter(report_type=report_type)
    
    # Filter by review status
    review_status = request.GET.get('review_status')
    if review_status == 'reviewed':
        reports = reports.filter(chat_blocks__reviewed_by_admin=True)
    elif review_status == 'unreviewed':
        reports = reports.filter(chat_blocks__reviewed_by_admin=False)
    
    # Search by username
    search = request.GET.get('search')
    if search:
        reports = reports.filter(
            Q(reporter__username__icontains=search) |
            Q(reported_user__username__icontains=search)
        )
    
    # Order by latest first
    reports = reports.order_by('-created_date')
    
    # Pagination
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get report types for filter dropdown
    report_types = MessageReport.REPORT_TYPES
    
    context = {
        'page_obj': page_obj,
        'report_types': report_types,
        'current_filters': {
            'report_type': report_type,
            'review_status': review_status,
            'search': search,
        }
    }
    return render(request, 'messaging/admin/reports_list.html', context)


@staff_member_required
def admin_report_detail(request, report_id):
    """Detailed view of a specific report with block/unblock actions"""
    report = get_object_or_404(MessageReport.objects.select_related(
        'reporter', 'reported_user'
    ), id=report_id)
    
    # Get existing chat block if any
    chat_block = ChatBlock.objects.filter(report=report).first()
    
    # Get messages between these users for context
    messages_between = Message.objects.filter(
        Q(sender=report.reporter, receiver=report.reported_user) |
        Q(sender=report.reported_user, receiver=report.reporter)
    ).select_related('sender', 'receiver').order_by('-timestamp')[:10]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'block':
            # Create or update chat block
            if chat_block:
                chat_block.is_active = True
                chat_block.reviewed_by_admin = True
                chat_block.admin_notes = admin_notes
                chat_block.save()
            else:
                chat_block = ChatBlock.objects.create(
                    reporter=report.reporter,
                    blocked_user=report.reported_user,
                    report=report,
                    is_active=True,
                    reviewed_by_admin=True,
                    admin_notes=admin_notes
                )
            
            messages.success(request, f'Chat blocked between {report.reporter.username} and {report.reported_user.username}')
            
        elif action == 'unblock':
            if chat_block:
                chat_block.is_active = False
                chat_block.reviewed_by_admin = True
                chat_block.admin_notes = admin_notes
                chat_block.save()
                
                messages.success(request, f'Chat unblocked between {report.reporter.username} and {report.reported_user.username}')
            else:
                messages.warning(request, 'No active block found')
                
        elif action == 'dismiss':
            # Mark as reviewed but don't block
            if chat_block:
                chat_block.reviewed_by_admin = True
                chat_block.admin_notes = admin_notes
                chat_block.save()
            else:
                # Create inactive block to mark as reviewed
                ChatBlock.objects.create(
                    reporter=report.reporter,
                    blocked_user=report.reported_user,
                    report=report,
                    is_active=False,
                    reviewed_by_admin=True,
                    admin_notes=admin_notes
                )
            
            messages.success(request, 'Report dismissed - no action taken')
        
        return redirect('messaging:admin_report_detail', report_id=report.id)
    
    context = {
        'report': report,
        'chat_block': chat_block,
        'messages_between': messages_between,
    }
    return render(request, 'messaging/admin/report_detail.html', context)


@staff_member_required
def admin_chat_blocks_list(request):
    """List all chat blocks with filtering"""
    blocks = ChatBlock.objects.select_related(
        'reporter', 'blocked_user', 'report'
    )
    
    # Filter by active status
    status = request.GET.get('status')
    if status == 'active':
        blocks = blocks.filter(is_active=True)
    elif status == 'inactive':
        blocks = blocks.filter(is_active=False)
    
    # Filter by review status
    review_status = request.GET.get('review_status')
    if review_status == 'reviewed':
        blocks = blocks.filter(reviewed_by_admin=True)
    elif review_status == 'unreviewed':
        blocks = blocks.filter(reviewed_by_admin=False)
    
    # Search by username
    search = request.GET.get('search')
    if search:
        blocks = blocks.filter(
            Q(reporter__username__icontains=search) |
            Q(blocked_user__username__icontains=search)
        )
    
    # Order by latest first
    blocks = blocks.order_by('-created_date')
    
    # Pagination
    paginator = Paginator(blocks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_filters': {
            'status': status,
            'review_status': review_status,
            'search': search,
        }
    }
    return render(request, 'messaging/admin/chat_blocks_list.html', context)


@staff_member_required
@require_POST
def admin_toggle_block(request, block_id):
    """Toggle chat block active/inactive status"""
    block = get_object_or_404(ChatBlock, id=block_id)
    
    action = request.POST.get('action')
    admin_notes = request.POST.get('admin_notes', block.admin_notes)
    
    if action == 'toggle':
        block.is_active = not block.is_active
        block.reviewed_by_admin = True
        block.admin_notes = admin_notes
        block.save()
        
        status_text = 'activated' if block.is_active else 'deactivated'
        messages.success(request, f'Chat block {status_text} for {block.reporter.username} ↔ {block.blocked_user.username}')
    
    # Redirect back to the referring page or blocks list
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'messaging:admin_chat_blocks_list'
    return redirect(next_url)


# ============================================
# USER MANAGEMENT ADMIN VIEWS
# ============================================

@staff_member_required
def admin_users_list(request):
    """Admin view to list and filter all users"""
    from django.contrib.auth.models import User
    from profiles.models import UserProfile
    
    # Get filter parameters
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # Base queryset with profile
    users = User.objects.select_related('profile').order_by('-date_joined')
    
    # Apply status filter
    if status == 'active':
        users = users.filter(profile__is_verified=True, profile__is_suspended=False, profile__is_deleted=False)
    elif status == 'suspended':
        users = users.filter(profile__is_suspended=True)
    elif status == 'deleted':
        users = users.filter(profile__is_deleted=True)
    elif status == 'pending':
        users = users.filter(profile__is_verified=False, profile__is_suspended=False, profile__is_deleted=False)
    
    # Apply search filter
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Status choices for filter
    status_choices = [
        ('', 'All Users'),
        ('active', 'Active'),
        ('pending', 'Pending Verification'),
        ('suspended', 'Suspended'),
        ('deleted', 'Deleted'),
    ]
    
    context = {
        'page_obj': page_obj,
        'status_choices': status_choices,
        'current_filters': {
            'status': status,
            'search': search,
        },
    }
    return render(request, 'messaging/admin/users_list.html', context)


@staff_member_required
def admin_user_detail(request, user_id):
    """Admin view to manage individual user"""
    from django.contrib.auth.models import User
    from profiles.models import UserProfile
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    profile = user.profile
    
    # Get user statistics
    from messaging.models import Message, MessageReport
    
    stats = {
        'messages_sent': Message.objects.filter(sender=user).count(),
        'messages_received': Message.objects.filter(receiver=user).count(),
        'reports_made': MessageReport.objects.filter(reporter=user).count(),
        'reports_received': MessageReport.objects.filter(reported_user=user).count(),
        'referrals_sent': profile.user.sent_referrals.count() if hasattr(profile.user, 'sent_referrals') else 0,
        'referrals_received': profile.referral_count,
    }
    
    context = {
        'user_obj': user,  # renamed to avoid conflict with request.user
        'profile': profile,
        'stats': stats,
    }
    return render(request, 'messaging/admin/user_detail.html', context)


@staff_member_required
@require_POST
def admin_suspend_user(request, user_id):
    """Suspend a user account"""
    from django.contrib.auth.models import User
    from audittrack.views import log_audit_action
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    if user.is_superuser:
        messages.error(request, 'Cannot suspend superuser accounts.')
        return redirect('messaging:admin_user_detail', user_id=user_id)
    
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Suspension reason is required.')
        return redirect('messaging:admin_user_detail', user_id=user_id)
    
    # Suspend the user
    user.profile.suspend_user(request.user, reason)
    
    # Log audit event
    log_audit_action(
        user=request.user,
        action='user_suspension',
        action_detail=f'Suspended user {user.username}: {reason}'
    )
    
    messages.success(request, f'User {user.username} has been suspended.')
    return redirect('messaging:admin_user_detail', user_id=user_id)


@staff_member_required
@require_POST
def admin_unsuspend_user(request, user_id):
    """Unsuspend a user account"""
    from django.contrib.auth.models import User
    from audittrack.views import log_audit_action
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    # Unsuspend the user
    user.profile.unsuspend_user()
    
    # Log audit event
    log_audit_action(
        user=request.user,
        action='user_unsuspension',
        action_detail=f'Unsuspended user {user.username}'
    )
    
    messages.success(request, f'User {user.username} has been unsuspended.')
    return redirect('messaging:admin_user_detail', user_id=user_id)



@staff_member_required
@require_POST
def admin_restore_user(request, user_id):
    """Restore a soft deleted user"""
    from django.contrib.auth.models import User
    from audittrack.views import log_audit_action
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    # Restore the user
    user.profile.restore_user()
    
    # Log audit event
    log_audit_action(
        user=request.user,
        action='user_restoration',
        action_detail=f'Restored user {user.username}'
    )
    
    messages.success(request, f'User {user.username} has been restored.')
    return redirect('messaging:admin_user_detail', user_id=user_id)


@login_required
@require_http_methods(["GET", "POST"])
def chat_heading_api(request, user_id):
    """API endpoint to get or set chat heading for a conversation"""
    other_user = get_object_or_404(User, id=user_id)
    message_type_id = request.GET.get('message_type_id') or request.POST.get('message_type_id')
    
    # Get message type if specified
    message_type = None
    if message_type_id and message_type_id != 'null':
        try:
            message_type = MessageType.objects.get(id=message_type_id)
        except MessageType.DoesNotExist:
            pass
    
    if request.method == 'GET':
        # Get current heading
        heading = ChatHeading.get_heading_for_chat(request.user, other_user, message_type)
        return JsonResponse({
            'success': True,
            'heading': heading
        })
    
    elif request.method == 'POST':
        # Set/update heading
        try:
            data = json.loads(request.body)
            heading = data.get('heading', '').strip()
            
            if heading:
                # Set or update heading
                ChatHeading.set_heading_for_chat(request.user, other_user, message_type, heading)
                return JsonResponse({
                    'success': True,
                    'message': 'Chat heading updated successfully',
                    'heading': heading
                })
            else:
                # Remove heading
                ChatHeading.set_heading_for_chat(request.user, other_user, message_type, None)
                return JsonResponse({
                    'success': True,
                    'message': 'Chat heading removed successfully',
                    'heading': None
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
@require_http_methods(["GET"])
def user_info_api(request, user_id):
    """API endpoint to get user info including last login time"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        return JsonResponse({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'last_login': user.last_login.isoformat() if user.last_login else None
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)