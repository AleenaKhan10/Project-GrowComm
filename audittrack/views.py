from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import AuditEvent, FocusLog


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
    events = AuditEvent.objects.select_related('user', 'target_user').all()
    
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
            'target_user': event.target_user.username if event.target_user else None,
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


@login_required
def focus_test_page(request):
    """
    Test page for focus tracking functionality.
    """
    return render(request, 'audittrack/focus_test.html')


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


@require_http_methods(["POST"])
@login_required
def log_focus_event(request):
    """
    API endpoint to log page focus events.
    
    Expects JSON: {
        "event_type": "focus_start" or "focus_end",
        "page_url": "current page URL",
        "page_title": "page title (optional)",
        "session_id": "browser session ID (optional)"
    }
    """
    import json
    
    try:
        data = json.loads(request.body)
        event_type = data.get('event_type')
        page_url = data.get('page_url')
        page_title = data.get('page_title', '')
        session_id = data.get('session_id', '')
        
        # Validate required fields
        if not event_type or not page_url:
            return JsonResponse({
                'error': 'event_type and page_url are required'
            }, status=400)
        
        # Validate event type
        valid_events = ['focus_start', 'focus_end']
        if event_type not in valid_events:
            return JsonResponse({
                'error': 'Invalid event_type. Must be focus_start or focus_end'
            }, status=400)
        
        # Get client info
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = request.META.get('REMOTE_ADDR')
        
        # Create focus log entry
        focus_log = FocusLog.log_focus_event(
            user=request.user,
            page_url=page_url,
            event_type=event_type,
            page_title=page_title,
            session_id=session_id,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Also log to main AuditEvent table
        audit_action = 'page_focus_start' if event_type == 'focus_start' else 'page_focus_end'
        audit_detail = f"{page_title or 'Page'} - {page_url}"
        AuditEvent.log_action(
            user=request.user,
            action=audit_action,
            action_detail=audit_detail
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Focus event {event_type} logged successfully',
            'log_id': focus_log.id,
            'timestamp': focus_log.timestamp.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_focus_statistics(request):
    """
    Get user focus statistics.
    
    Query params:
    - filter: 'today', 'last_24_hours', 'last_6_days', 'last_30_days'
    - user_id: optional, filter by specific user (admin only)
    """
    filter_type = request.GET.get('filter', 'today')
    user_id = request.GET.get('user_id')
    
    start_time = get_time_filter(filter_type)
    
    # Determine which user(s) to analyze
    if user_id and request.user.is_staff:
        # Admin can view any user's stats
        from django.contrib.auth.models import User
        try:
            target_user = User.objects.get(id=user_id)
            focus_duration = FocusLog.get_user_focus_duration(target_user, start_time)
            total_sessions = FocusLog.objects.filter(
                user=target_user,
                event_type='focus_start',
                timestamp__gte=start_time
            ).count()
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
    else:
        # Regular users can only view their own stats
        target_user = request.user
        focus_duration = FocusLog.get_user_focus_duration(target_user, start_time)
        total_sessions = FocusLog.objects.filter(
            user=target_user,
            event_type='focus_start',
            timestamp__gte=start_time
        ).count()
    
    # Convert duration to human readable format
    hours = int(focus_duration // 3600)
    minutes = int((focus_duration % 3600) // 60)
    seconds = int(focus_duration % 60)
    
    stats = {
        'user': target_user.username,
        'total_focus_duration_seconds': focus_duration,
        'total_focus_duration_formatted': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
        'total_focus_sessions': total_sessions,
        'average_session_duration': round(focus_duration / total_sessions, 2) if total_sessions > 0 else 0,
        'filter_applied': filter_type,
        'period_start': start_time.isoformat(),
        'period_end': timezone.now().isoformat()
    }
    
    return JsonResponse(stats)


@login_required
def get_focus_logs(request):
    """
    Get paginated focus logs.
    
    Query params:
    - page: page number
    - per_page: items per page
    - user_id: filter by user (admin only)
    - event_type: filter by event type
    """
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    user_id = request.GET.get('user_id')
    event_type = request.GET.get('event_type')
    
    # Build query
    logs = FocusLog.objects.select_related('user').all()
    
    # Apply filters
    if user_id and request.user.is_staff:
        logs = logs.filter(user_id=user_id)
    elif not request.user.is_staff:
        # Regular users can only see their own logs
        logs = logs.filter(user=request.user)
    
    if event_type:
        logs = logs.filter(event_type=event_type)
    
    # Paginate
    paginator = Paginator(logs, per_page)
    page_obj = paginator.get_page(page)
    
    # Convert to JSON
    logs_data = []
    for log in page_obj:
        logs_data.append({
            'id': log.id,
            'user': log.user.username,
            'page_url': log.page_url,
            'page_title': log.page_title,
            'event_type': log.get_event_type_display(),
            'timestamp': log.timestamp.isoformat(),
            'session_id': log.session_id
        })
    
    response_data = {
        'logs': logs_data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    }
    
    return JsonResponse(response_data)