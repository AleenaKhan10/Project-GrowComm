from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import AuditEvent


def log_audit_action(user, action, action_detail=""):
    """
    Utility function to log audit actions.
    
    Args:
        user: User instance who performed the action
        action: String matching one of the ACTION_CHOICES
        action_detail: Optional detail about the action
    """
    try:
        AuditEvent.objects.create(
            user=user,
            action=action,
            action_detail=action_detail
        )
        return True
    except Exception as e:
        print(f"Error logging audit action: {e}")
        return False


def get_time_filter(filter_type):
    """
    Get time range based on filter type.
    
    Args:
        filter_type: 'today', 'last_24_hours', 'last_6_days', 'last_30_days'
    
    Returns:
        datetime object representing the start time for filtering
    """
    now = timezone.now()
    
    if filter_type == 'today':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_type == 'last_24_hours':
        return now - timedelta(hours=24)
    elif filter_type == 'last_6_days':
        return now - timedelta(days=6)
    elif filter_type == 'last_30_days':
        return now - timedelta(days=30)
    else:
        # Default to today
        return now.replace(hour=0, minute=0, second=0, microsecond=0)


@login_required
def get_audit_statistics(request):
    """
    Get audit statistics with time filtering.
    
    Returns JSON with statistics for the 7 required metrics.
    """
    filter_type = request.GET.get('filter', 'today')
    start_time = get_time_filter(filter_type)
    
    # Filter events from start_time to now
    events = AuditEvent.objects.filter(timestamp__gte=start_time)
    
    # Calculate statistics for the 7 required metrics
    stats = {
        'total_signins': events.filter(action='user_signin').count(),
        'total_signouts': events.filter(action='user_signout').count(),
        'total_invites': events.filter(action='invite_created').count(),
        'total_registrations': events.filter(action='user_registered').count(),
        'total_referrals': events.filter(action='referral_sent').count(),
        'total_slots_opened': events.filter(action='slot_booked').count(),
        'total_users_deleted': events.filter(action='user_deleted').count(),
        'filter_applied': filter_type,
        'period_start': start_time.isoformat(),
        'period_end': timezone.now().isoformat()
    }
    
    return JsonResponse(stats)


@login_required 
def get_audit_logs(request):
    """
    Get paginated audit logs.
    
    Returns JSON with audit events and pagination info.
    """
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    
    # Get all audit events ordered by timestamp (newest first)
    events = AuditEvent.objects.select_related('user').all()
    
    # Paginate
    paginator = Paginator(events, per_page)
    page_obj = paginator.get_page(page)
    
    # Convert to JSON serializable format
    logs = []
    for event in page_obj:
        logs.append({
            'id': event.id,
            'user': event.user.username if event.user else "Deleted User",
            'action': event.get_action_display(),
            'action_detail': event.action_detail,
            'timestamp': event.timestamp.isoformat()
        })
    
    response_data = {
        'logs': logs,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    }
    
    return JsonResponse(response_data)


@login_required
def audit_dashboard(request):
    """
    Main dashboard view for audit tracking.
    """
    return render(request, 'audittrack/dashboard.html')


@require_http_methods(["POST"])
@login_required
def create_audit_log(request):
    """
    API endpoint to create a new audit log entry.
    
    Expects JSON: {
        "action": "action_type",
        "action_detail": "optional detail"
    }
    """
    import json
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        action_detail = data.get('action_detail', '')
        
        # Validate action type
        valid_actions = [choice[0] for choice in AuditEvent.ACTION_CHOICES]
        if action not in valid_actions:
            return JsonResponse({
                'error': 'Invalid action type',
                'valid_actions': valid_actions
            }, status=400)
        
        # Create audit event
        success = log_audit_action(request.user, action, action_detail)
        
        if success:
            return JsonResponse({'success': True, 'message': 'Audit log created'})
        else:
            return JsonResponse({'error': 'Failed to create audit log'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)