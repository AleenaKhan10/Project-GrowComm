from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
import json

from .models import Community, CommunityMembership
from profiles.forms import ProfileSearchForm
from messaging.models import Message, MessageType, MessageSlotBooking
from messaging.forms import MessageRequestForm


@login_required
def user_list(request):
    """Main community page showing all users with search and filter functionality"""
    form = ProfileSearchForm(request.GET)
    
    # Get all users except current user
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    
    # Apply filters if form is valid
    if form.is_valid():
        search = form.cleaned_data.get('search')
        organization_level = form.cleaned_data.get('organization_level')
        tags = form.cleaned_data.get('tags')
        
        if search:
            users = users.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(profile__company__icontains=search) |
                Q(profile__team__icontains=search) |
                Q(profile__bio__icontains=search) |
                Q(profile__tags__icontains=search) |
                Q(profile__schools__icontains=search)
            )
        
        if organization_level:
            users = users.filter(profile__organization_level=organization_level)
        
        if tags:
            tag_list = [tag.strip().lower() for tag in tags.split(',') if tag.strip()]
            for tag in tag_list:
                users = users.filter(profile__tags__icontains=tag)
    
    # Order by newest members first
    users = users.order_by('-profile__created_date')
    
    # Paginate results
    paginator = Paginator(users, 12)  # Show 12 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get message types and prepare slot availability data for each user
    message_types = MessageType.objects.filter(is_active=True)
    users_slot_data = {}
    
    for user in page_obj:
        if hasattr(user, 'message_settings'):
            try:
                slot_availability = user.message_settings.get_slot_availability_for_user(request.user)
                users_slot_data[user.id] = slot_availability
            except:
                users_slot_data[user.id] = {}
        else:
            users_slot_data[user.id] = {}
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_users': users.count(),
        'user_is_verified': request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_verified),
        'message_types': message_types,
        'users_slot_data': users_slot_data,
    }
    return render(request, 'communities/user_list.html', context)


@login_required
def community_list(request):
    """List all communities"""
    communities = Community.objects.filter(is_active=True)
    
    context = {
        'communities': communities,
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
    
    # Get message types for the form
    message_types = MessageType.objects.filter(is_active=True)
    
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
            # Get or create the message type
            message_type = None
            if message_type_name and message_type_name != 'General':
                message_type, _ = MessageType.objects.get_or_create(
                    name=message_type_name,
                    defaults={
                        'description': f'{message_type_name} message',
                        'is_active': True
                    }
                )
            
            # Check slot availability if message type is provided
            if message_type:
                can_send, reason = MessageSlotBooking.can_user_send_message(request.user, to_user, message_type)
                if not can_send:
                    error_messages = {
                        'already_sent': f'You have already sent a {message_type.name} message to {to_user.username}. Please wait 3 days before sending another.',
                        'slots_full': f'{to_user.username}\'s {message_type.name} slots are currently full. Please try again later.'
                    }
                    return JsonResponse({
                        'success': False,
                        'error': error_messages.get(reason, 'Cannot send message at this time')
                    }, status=400)
            
            # Create the message using the simplified model
            message = Message.objects.create(
                sender=request.user,
                receiver=to_user,
                content=message_content,
                message_type=message_type
            )
            
            # Book slot if message type is provided
            if message_type:
                booking, booking_reason = MessageSlotBooking.book_slot(
                    request.user, to_user, message_type, message
                )
                if not booking:
                    # If booking failed, delete the message and return error
                    message.delete()
                    return JsonResponse({
                        'success': False,
                        'error': f'Failed to send message: {booking_reason}'
                    }, status=400)
        
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