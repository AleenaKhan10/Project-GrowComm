from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from .models import InviteLink
from profiles.models import Referral
from communities.decorators import community_member_required


@community_member_required
def community_my_invites(request, community_id, community=None, membership=None):
    """View user's invites within community context"""
    from profiles.forms import SendReferralForm
    from invites.forms import CreateInviteForm
    from audittrack.utils import log_invite_created, log_referral_sent
    
    # Get invites created by current user for this community
    invites = InviteLink.objects.filter(
        created_by=request.user,
        community=community
    ).order_by('-created_date')
    
    # Get user's profile
    profile = request.user.profile
    
    # Get referrals
    received_referrals = Referral.objects.filter(
        recipient_user=request.user
    ).select_related('sender').order_by('-created_at')
    
    sent_referrals = Referral.objects.filter(
        sender=request.user
    ).select_related('recipient_user').order_by('-created_at')
    
    # Handle form submissions
    invite_form = CreateInviteForm()
    referral_form = SendReferralForm(user=request.user)
    
    if request.method == 'POST':
        if 'create_invite' in request.POST:
            invite_form = CreateInviteForm(request.POST)
            if invite_form.is_valid():
                # Create invite with the current community context
                expires_in_days = invite_form.cleaned_data['expires_in_days']
                from datetime import datetime, timedelta
                expiry_date = datetime.now() + timedelta(days=expires_in_days)
                
                invite = InviteLink.objects.create(
                    created_by=request.user,
                    community=community,
                    expiry_date=expiry_date
                )
                
                from invites.utils import build_invite_url
                invite_url = build_invite_url(request, invite.code)
                log_invite_created(request.user, f"Created invite: {invite.code}")
                messages.success(
                    request, 
                    f'Invite link created successfully! Share this link: {invite_url}'
                )
                return redirect('invites:community_my_invites', community_id=community_id)
        
        elif 'send_referral' in request.POST:
            # Check if user is verified before sending referral (superadmins bypass)
            if not request.user.is_superuser and not request.user.profile.is_verified:
                messages.error(request, f"You need {request.user.profile.referrals_needed} more referrals to send referrals to others.")
                return redirect('invites:community_my_invites', community_id=community_id)
            
            referral_form = SendReferralForm(user=request.user, data=request.POST)
            if referral_form.is_valid():
                try:
                    referral = referral_form.save()
                    log_referral_sent(request.user, f"Sent referral to {referral.recipient_email}")
                    messages.success(
                        request, 
                        f'Referral sent successfully to {referral.recipient_email}!'
                    )
                    return redirect('invites:community_my_invites', community_id=community_id)
                except Exception as e:
                    messages.error(request, f'Failed to send referral: {str(e)}')
            else:
                # Show specific form errors for debugging
                for field, errors in referral_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Referral {field}: {error}')
    
    context = {
        'invite_form': invite_form,
        'referral_form': referral_form,
        'invites': invites,
        'profile': profile,
        'received_referrals': received_referrals,
        'sent_referrals': sent_referrals,
        'verification_status': {
            'is_verified': request.user.is_superuser or profile.is_verified,
            'referral_count': profile.referral_count,
            'referrals_needed': 0 if request.user.is_superuser else profile.referrals_needed,
            'needs_referrals': False if request.user.is_superuser else profile.needs_referrals,
        },
        'community': community,
        'community_id': community_id,
        'membership': membership,
    }
    return render(request, 'invites/my_invites.html', context)


@community_member_required
def community_invite_detail(request, community_id, invite_id, community=None, membership=None):
    """View invite details within community context"""
    invite = get_object_or_404(InviteLink, id=invite_id, created_by=request.user, community=community)
    
    context = {
        'invite': invite,
        'community': community,
        'community_id': community_id,
        'membership': membership,
    }
    return render(request, 'invites/invite_detail.html', context)


@community_member_required
def community_referral_status(request, community_id, community=None, membership=None):
    """View referral status within community context"""
    # Get user's profile
    profile = request.user.profile
    
    # Get referrals received by current user
    received_referrals = Referral.objects.filter(
        recipient_user=request.user
    ).select_related('sender').order_by('-created_at')
    
    # Get referrals sent by current user
    sent_referrals = Referral.objects.filter(
        sender=request.user
    ).select_related('recipient_user').order_by('-created_at')
    
    context = {
        'profile': profile,
        'received_referrals': received_referrals,
        'sent_referrals': sent_referrals,
        'verification_status': {
            'is_verified': request.user.is_superuser or profile.is_verified,
            'referral_count': profile.referral_count,
            'referrals_needed': 0 if request.user.is_superuser else profile.referrals_needed,
            'needs_referrals': False if request.user.is_superuser else profile.needs_referrals,
        },
        'community': community,
        'community_id': community_id,
        'membership': membership,
    }
    return render(request, 'invites/referral_status.html', context)