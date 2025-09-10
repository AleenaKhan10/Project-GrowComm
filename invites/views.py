from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import InviteLink, ReferralApproval
from .forms import CreateInviteForm
from .utils import build_invite_url
from profiles.decorators import verified_user_required
from profiles.models import Referral
from profiles.forms import SendReferralForm
from audittrack.utils import log_invite_created, log_referral_sent


@login_required
def my_invites(request):
    """Combined view for invites and referrals management"""
    user_invites = InviteLink.objects.filter(created_by=request.user)
    
    # Get referral data
    profile = request.user.profile
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
            # Allow all users to create invites (no verification required)
            invite_form = CreateInviteForm(request.POST)
            if invite_form.is_valid():
                invite = invite_form.save(user=request.user)
                invite_url = build_invite_url(request, invite.code)
                log_invite_created(request.user, f"Created invite: {invite.code}")
                messages.success(
                    request, 
                    f'Invite link created successfully! Share this link: {invite_url}'
                )
                return redirect('invites:my_invites')
        
        elif 'send_referral' in request.POST:
            # Check if user is verified before sending referral (superadmins bypass)
            if not request.user.is_superuser and not request.user.profile.is_verified:
                messages.error(request, f"You need {request.user.profile.referrals_needed} more referrals to send referrals to others.")
                return redirect('invites:my_invites')
            
            referral_form = SendReferralForm(user=request.user, data=request.POST)
            if referral_form.is_valid():
                try:
                    referral = referral_form.save()
                    log_referral_sent(request.user, f"Sent referral to {referral.recipient_email}")
                    messages.success(
                        request, 
                        f'Referral sent successfully to {referral.recipient_email}!'
                    )
                    return redirect('invites:my_invites')
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
        'invites': user_invites,
        'profile': profile,
        'received_referrals': received_referrals,
        'sent_referrals': sent_referrals,
        'verification_status': {
            'is_verified': request.user.is_superuser or profile.is_verified,
            'referral_count': profile.referral_count,
            'referrals_needed': 0 if request.user.is_superuser else profile.referrals_needed,
            'needs_referrals': False if request.user.is_superuser else profile.needs_referrals,
        }
    }
    return render(request, 'invites/my_invites.html', context)


@login_required
def invite_detail(request, invite_id):
    """View details of a specific invite"""
    invite = get_object_or_404(InviteLink, id=invite_id, created_by=request.user)
    
    # Build the full invite URL
    invite_url = build_invite_url(request, invite.code)
    
    context = {
        'invite': invite,
        'invite_url': invite_url,
    }
    return render(request, 'invites/invite_detail.html', context)


@login_required
def referral_status(request):
    """View referral approval status for users invited by current user"""
    referrals = ReferralApproval.objects.filter(inviter=request.user).order_by('-created_date')
    
    context = {
        'referrals': referrals,
    }
    return render(request, 'invites/referral_status.html', context)
