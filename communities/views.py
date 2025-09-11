from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
import json

from .models import Community, CommunityMembership
from profiles.forms import ProfileSearchForm
from messaging.models import Message, MessageType, MessageSlotBooking, UserMessageSettings, CustomMessageSlot
from messaging.forms import MessageRequestForm
from audittrack.utils import log_slot_booked, log_message_answered


@login_required
def user_list(request):
    """Main community page showing all users with unified search functionality"""
    # Get the unified search query
    search_query = request.GET.get('q', '').strip()
    
    # Get all users except current user
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    
    # Apply unified search if provided
    if search_query:
        # Split search query into words for better matching
        search_words = search_query.split()
        
        # Build search filter using OR logic - users matching ANY word will be returned
        search_filter = Q()
        for word in search_words:
            word_lower = word.lower()
            
            # Create basic field searches
            word_filter = (
                Q(first_name__icontains=word) |
                Q(last_name__icontains=word) |
                Q(username__icontains=word) |
                Q(profile__company__icontains=word) |
                Q(profile__team__icontains=word) |
                Q(profile__location__icontains=word) |
                Q(profile__bio__icontains=word) |
                Q(profile__tags__icontains=word) |
                Q(profile__schools__icontains=word) |
                Q(profile__organization_level__icontains=word)
            )
            
            # Add special handling for organization level display names
            from profiles.models import UserProfile
            org_level_matches = Q()
            for key, display_name in UserProfile.ORGANIZATION_LEVELS:
                if word_lower in display_name.lower():
                    org_level_matches |= Q(profile__organization_level=key)
            
            word_filter |= org_level_matches
            # Use OR logic - users matching ANY search word will be included
            search_filter |= word_filter
        
        users = users.filter(search_filter).distinct()
    
    # Keep the old form for backward compatibility but hidden
    form = ProfileSearchForm(request.GET)
    
    # Order by newest members first
    users = users.order_by('-profile__created_date')
    
    # No default message types - all categories are now custom per user
    message_types = []
    users_slot_data = {}
    
    def make_json_safe(obj):
        """Recursively convert objects to JSON-serializable types"""
        from django.db import models
        
        if isinstance(obj, models.Model):
            # Convert Django model instances to their name/string representation
            return str(obj)
        elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
            # Convert other objects with __dict__ to string
            return str(obj)
        elif isinstance(obj, dict):
            return {str(key): make_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_json_safe(item) for item in obj]
        else:
            return obj

    for user in users:
        try:
            # Get or create user message settings
            from messaging.models import UserMessageSettings
            settings, created = UserMessageSettings.objects.get_or_create(user=user)
            slot_availability = settings.get_slot_availability_for_user(request.user)
            # Convert to JSON-serializable format recursively
            users_slot_data[user.id] = make_json_safe(slot_availability)
        except Exception as e:
            # Fallback to user profile's current slot configuration
            try:
                available_slots = user.profile.available_slots
                users_slot_data[user.id] = make_json_safe(available_slots)
            except:
                users_slot_data[user.id] = {}
    
    
    context = {
        'form': form,
        'search_query': search_query,
        'users': users,
        'total_users': users.count(),
        'user_is_verified': request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_verified),
        'user_can_send': request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_verified and not request.user.profile.is_suspended),
        'message_types': message_types,
        'users_slot_data': users_slot_data,
        'users_slot_data_json': json.dumps(users_slot_data, default=str),
    }
    return render(request, 'communities/user_list.html', context)


@login_required
def community_list(request):
    """List all communities"""
    communities = Community.objects.filter(is_active=True)
    
    # Get total user count
    total_users = User.objects.filter(is_active=True).count()
    
    context = {
        'communities': communities,
        'total_users': total_users,
    }
    return render(request, 'communities/community_list.html', context)


@login_required
def community_detail(request, community_id):
    """View a specific community and its members"""
    community = get_object_or_404(Community, id=community_id, is_active=True)
    
    # Check if user is a member
    is_member = CommunityMembership.objects.filter(
        user=request.user,
        community=community,
        is_active=True
    ).exists()
    
    # Get community members
    members = community.active_members.select_related('profile')
    
    context = {
        'community': community,
        'is_member': is_member,
        'members': members,
    }
    return render(request, 'communities/community_detail.html', context)


@login_required
def join_community(request, community_id):
    """Join a community"""
    community = get_object_or_404(Community, id=community_id, is_active=True)
    
    # Check if already a member
    membership, created = CommunityMembership.objects.get_or_create(
        user=request.user,
        community=community,
        defaults={'is_active': True}
    )
    
    if created:
        messages.success(request, f'You have successfully joined {community.name}!')
    elif not membership.is_active:
        membership.is_active = True
        membership.save()
        messages.success(request, f'Welcome back to {community.name}!')
    else:
        messages.info(request, f'You are already a member of {community.name}.')
    
    return redirect('communities:community_detail', community_id=community.id)


@login_required
def leave_community(request, community_id):
    """Leave a community"""
    community = get_object_or_404(Community, id=community_id, is_active=True)
    
    try:
        membership = CommunityMembership.objects.get(
            user=request.user,
            community=community,
            is_active=True
        )
        membership.is_active = False
        membership.save()
        messages.success(request, f'You have left {community.name}.')
    except CommunityMembership.DoesNotExist:
        messages.error(request, f'You are not a member of {community.name}.')
    
    return redirect('communities:community_detail', community_id=community.id)


@login_required
def user_detail(request, user_id):
    """View user details with messaging functionality from community page"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Handle direct message sending
        content = request.POST.get('message_content', '').strip()
        message_type_name = request.POST.get('message_type', 'General')
        
        if content:
            # Get or create message type
            message_type, _ = MessageType.objects.get_or_create(
                name=message_type_name,
                defaults={'description': f'{message_type_name} message', 'is_active': True}
            )
            
            # Create the message
            Message.objects.create(
                sender=request.user,
                receiver=user,
                content=content,
                message_type=message_type
            )
            
            messages.success(
                request, 
                f'Message sent to {user.username}! '
                f'You can view the conversation in your inbox.'
            )
            return redirect('messaging:conversation', user_id=user.id)
    
    # Get available slots for current user (if profile exists)
    available_slots = None
    if hasattr(request.user, 'profile'):
        available_slots = request.user.profile.available_slots
    
    # Get user's custom message slots for the form
    custom_slots = CustomMessageSlot.objects.filter(
        user=user, 
        is_active=True
    ).order_by('name')
    message_types = [{'name': slot.name} for slot in custom_slots]
    
    context = {
        'profile_user': user,
        'message_types': message_types,
        'available_slots': available_slots,
    }
    return render(request, 'communities/user_detail.html', context)


@login_required
@require_http_methods(["POST"])
def send_inline_message(request):
    """
    Handle inline message sending via AJAX from community page.
    Creates direct message between users using the simplified Message model.
    """
    try:
        # Check if user is verified before allowing message sending (superadmins bypass)
        if not request.user.is_superuser and (not hasattr(request.user, 'profile') or not request.user.profile.is_verified):
            referrals_needed = request.user.profile.referrals_needed if hasattr(request.user, 'profile') else 3
            return JsonResponse({
                'success': False,
                'error': f'You need {referrals_needed} more referrals to send messages.',
                'verification_required': True
            }, status=403)
        
        data = json.loads(request.body)
        to_user_id = data.get('to_user_id')
        message_type_name = data.get('message_type', 'General')
        message_content = data.get('message_content', '').strip()
        
        # Validate input
        if not to_user_id:
            return JsonResponse({
                'success': False,
                'error': 'Receiver ID is required'
            }, status=400)
        
        if not message_content:
            return JsonResponse({
                'success': False,
                'error': 'Message content cannot be empty'
            }, status=400)
        
        # Get the recipient user
        try:
            to_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            }, status=404)
        
        # Don't allow messaging yourself
        if to_user == request.user:
            return JsonResponse({
                'success': False,
                'error': 'You cannot send a message to yourself'
            }, status=400)
        
        with transaction.atomic():
            # Get receiver's message settings
            receiver_settings, _ = UserMessageSettings.objects.get_or_create(user=to_user)
            
            message_type = None
            if message_type_name:
                # For custom slots, use the special naming convention
                custom_slot = CustomMessageSlot.objects.filter(
                    user=to_user,
                    name=message_type_name,
                    is_active=True
                ).first()
                
                if custom_slot:
                    # Create/get message type with custom naming convention
                    message_type, _ = MessageType.objects.get_or_create(
                        name=f"CUSTOM_{to_user.id}_{message_type_name}",
                        defaults={
                            'description': f'Custom slot: {message_type_name} for {to_user.username}',
                            'is_active': True
                        }
                    )
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Message category "{message_type_name}" not found for {to_user.username}'
                    }, status=400)
            
            # Check slot availability for new messages only
            if message_type:
                can_send, reason = MessageSlotBooking.can_user_send_message(request.user, to_user, message_type)
                if not can_send:
                    error_messages = {
                        'already_sent': f'You have already sent a {message_type_name} message to {to_user.username}. Please wait 3 days before sending another.',
                        'slots_full': f'{to_user.username}\'s {message_type_name} slots are currently full. Please try again later.',
                        'invalid_slot_type': f'Invalid message category "{message_type_name}".'
                    }
                    return JsonResponse({
                        'success': False,
                        'error': error_messages.get(reason, 'Cannot send message at this time')
                    }, status=400)
                
                # Book the slot first
                booking, booking_reason = MessageSlotBooking.book_slot(
                    request.user, to_user, message_type, None
                )
                if not booking:
                    return JsonResponse({
                        'success': False,
                        'error': f'Failed to book slot: {booking_reason}'
                    }, status=400)
                else:
                    # Log slot booking audit event
                    log_slot_booked(request.user, f"Booked {message_type_name} slot with {to_user.username} from community page")
            
            # Check if this is the first time responding to this user with this message type
            is_first_response = False
            if message_type:
                is_first_response = not Message.objects.filter(
                    sender=request.user,
                    receiver=to_user,
                    message_type=message_type
                ).exists()
            
            # Create the message
            message = Message.objects.create(
                sender=request.user,
                receiver=to_user,
                content=message_content,
                message_type=message_type
            )
            
            # Log first time message answer if this is a response to an existing conversation
            if is_first_response and message_type:
                # Check if there are messages from the receiver to the sender (indicating this is a response)
                has_received_messages = Message.objects.filter(
                    sender=to_user,
                    receiver=request.user,
                    message_type=message_type
                ).exists()
                
                if has_received_messages:
                    log_message_answered(request.user, f"First response to {to_user.username} in {message_type_name} category from community page")
            
            # Update the booking to reference the message
            if message_type and booking:
                booking.message = message
                booking.save()
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully!',
            'message_id': message.id,
            'conversation_url': f'/messaging/conversation/{to_user.id}/'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        import traceback
        print(f"Error in send_inline_message: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while sending the message'
        }, status=500)