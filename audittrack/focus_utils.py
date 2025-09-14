"""
Utility functions for focus tracking functionality.
"""

from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from .models import FocusLog


def log_focus_start(user, page_url, page_title="", session_id="", user_agent="", ip_address=None):
    """
    Log when a user starts focusing on a page.
    
    Args:
        user: User instance
        page_url: URL of the page
        page_title: Title of the page (optional)
        session_id: Browser session ID (optional)
        user_agent: Browser user agent (optional)
        ip_address: User's IP address (optional)
        
    Returns:
        FocusLog instance
    """
    return FocusLog.log_focus_event(
        user=user,
        page_url=page_url,
        event_type='focus_start',
        page_title=page_title,
        session_id=session_id,
        user_agent=user_agent,
        ip_address=ip_address
    )


def log_focus_end(user, page_url, page_title="", session_id="", user_agent="", ip_address=None):
    """
    Log when a user stops focusing on a page.
    
    Args:
        user: User instance
        page_url: URL of the page
        page_title: Title of the page (optional)
        session_id: Browser session ID (optional)
        user_agent: Browser user agent (optional)
        ip_address: User's IP address (optional)
        
    Returns:
        FocusLog instance
    """
    return FocusLog.log_focus_event(
        user=user,
        page_url=page_url,
        event_type='focus_end',
        page_title=page_title,
        session_id=session_id,
        user_agent=user_agent,
        ip_address=ip_address
    )


def get_user_daily_focus_time(user, date=None):
    """
    Get total focus time for a user on a specific date.
    
    Args:
        user: User instance
        date: Date object (defaults to today)
        
    Returns:
        Total focus duration in seconds
    """
    if date is None:
        date = timezone.now().date()
    
    start_time = datetime.combine(date, datetime.min.time())
    end_time = datetime.combine(date, datetime.max.time())
    
    if timezone.is_aware(timezone.now()):
        start_time = timezone.make_aware(start_time)
        end_time = timezone.make_aware(end_time)
    
    return FocusLog.get_user_focus_duration(user, start_time, end_time)


def get_user_weekly_focus_stats(user, start_of_week=None):
    """
    Get focus statistics for a user for the current week.
    
    Args:
        user: User instance
        start_of_week: Date of Monday of the week (defaults to current week)
        
    Returns:
        Dictionary with weekly focus statistics
    """
    if start_of_week is None:
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
    
    end_of_week = start_of_week + timedelta(days=6)
    
    start_time = datetime.combine(start_of_week, datetime.min.time())
    end_time = datetime.combine(end_of_week, datetime.max.time())
    
    if timezone.is_aware(timezone.now()):
        start_time = timezone.make_aware(start_time)
        end_time = timezone.make_aware(end_time)
    
    total_duration = FocusLog.get_user_focus_duration(user, start_time, end_time)
    total_sessions = FocusLog.objects.filter(
        user=user,
        event_type='focus_start',
        timestamp__gte=start_time,
        timestamp__lte=end_time
    ).count()
    
    # Calculate daily breakdown
    daily_stats = {}
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        daily_focus = get_user_daily_focus_time(user, day)
        daily_stats[day.strftime('%A')] = {
            'date': day,
            'focus_duration': daily_focus,
            'focus_duration_formatted': format_duration(daily_focus)
        }
    
    return {
        'user': user.username,
        'week_start': start_of_week,
        'week_end': end_of_week,
        'total_focus_duration': total_duration,
        'total_focus_duration_formatted': format_duration(total_duration),
        'total_sessions': total_sessions,
        'average_session_duration': total_duration / total_sessions if total_sessions > 0 else 0,
        'daily_breakdown': daily_stats
    }


def get_most_focused_pages(user, start_time=None, end_time=None, limit=10):
    """
    Get the pages where the user spends the most time focused.
    
    Args:
        user: User instance
        start_time: Optional start datetime filter
        end_time: Optional end datetime filter
        limit: Number of top pages to return
        
    Returns:
        List of dictionaries with page focus statistics
    """
    focus_events = FocusLog.objects.filter(user=user)
    
    if start_time:
        focus_events = focus_events.filter(timestamp__gte=start_time)
    if end_time:
        focus_events = focus_events.filter(timestamp__lte=end_time)
    
    focus_events = focus_events.order_by('timestamp')
    
    # Calculate focus duration per page
    page_durations = {}
    page_sessions = {}
    current_focus = {}
    
    for event in focus_events:
        page_key = event.page_url
        
        if event.event_type == 'focus_start':
            current_focus[page_key] = event.timestamp
        elif event.event_type == 'focus_end' and page_key in current_focus:
            duration = (event.timestamp - current_focus[page_key]).total_seconds()
            
            if page_key not in page_durations:
                page_durations[page_key] = 0
                page_sessions[page_key] = {'count': 0, 'title': event.page_title}
            
            page_durations[page_key] += duration
            page_sessions[page_key]['count'] += 1
            del current_focus[page_key]
    
    # Sort pages by total focus time
    sorted_pages = sorted(
        page_durations.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]
    
    # Format results
    results = []
    for page_url, total_duration in sorted_pages:
        session_info = page_sessions.get(page_url, {'count': 0, 'title': ''})
        results.append({
            'page_url': page_url,
            'page_title': session_info['title'],
            'total_focus_duration': total_duration,
            'total_focus_duration_formatted': format_duration(total_duration),
            'session_count': session_info['count'],
            'average_session_duration': total_duration / session_info['count'] if session_info['count'] > 0 else 0
        })
    
    return results


def get_focus_patterns(user, days_back=7):
    """
    Analyze user's focus patterns over time.
    
    Args:
        user: User instance
        days_back: Number of days to analyze
        
    Returns:
        Dictionary with focus pattern analysis
    """
    end_time = timezone.now()
    start_time = end_time - timedelta(days=days_back)
    
    focus_events = FocusLog.objects.filter(
        user=user,
        timestamp__gte=start_time,
        timestamp__lte=end_time
    ).order_by('timestamp')
    
    # Analyze by hour of day
    hourly_patterns = {i: {'sessions': 0, 'total_duration': 0} for i in range(24)}
    
    # Analyze by day of week
    daily_patterns = {i: {'sessions': 0, 'total_duration': 0} for i in range(7)}  # 0=Monday
    
    current_session = None
    
    for event in focus_events:
        hour = event.timestamp.hour
        day_of_week = event.timestamp.weekday()
        
        if event.event_type == 'focus_start':
            current_session = {
                'start_time': event.timestamp,
                'hour': hour,
                'day_of_week': day_of_week
            }
            hourly_patterns[hour]['sessions'] += 1
            daily_patterns[day_of_week]['sessions'] += 1
            
        elif event.event_type == 'focus_end' and current_session:
            duration = (event.timestamp - current_session['start_time']).total_seconds()
            hourly_patterns[current_session['hour']]['total_duration'] += duration
            daily_patterns[current_session['day_of_week']]['total_duration'] += duration
            current_session = None
    
    # Find peak hours
    peak_hour = max(hourly_patterns.items(), key=lambda x: x[1]['total_duration'])
    peak_day = max(daily_patterns.items(), key=lambda x: x[1]['total_duration'])
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    return {
        'user': user.username,
        'analysis_period_days': days_back,
        'hourly_patterns': hourly_patterns,
        'daily_patterns': daily_patterns,
        'peak_hour': {
            'hour': peak_hour[0],
            'duration': peak_hour[1]['total_duration'],
            'sessions': peak_hour[1]['sessions']
        },
        'peak_day': {
            'day': day_names[peak_day[0]],
            'duration': peak_day[1]['total_duration'],
            'sessions': peak_day[1]['sessions']
        }
    }


def format_duration(seconds):
    """
    Format duration in seconds to human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2h 15m 30s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds // 3600)
        remaining_seconds = seconds % 3600
        minutes = int(remaining_seconds // 60)
        final_seconds = int(remaining_seconds % 60)
        return f"{hours}h {minutes}m {final_seconds}s"


def cleanup_old_focus_logs(days_to_keep=90):
    """
    Clean up old focus logs to prevent database bloat.
    
    Args:
        days_to_keep: Number of days of logs to retain
        
    Returns:
        Number of deleted records
    """
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    deleted_count, _ = FocusLog.objects.filter(timestamp__lt=cutoff_date).delete()
    return deleted_count


def get_team_focus_leaderboard(users=None, start_time=None, end_time=None, limit=10):
    """
    Get a leaderboard of users by focus time.
    
    Args:
        users: QuerySet of users to include (defaults to all users)
        start_time: Optional start datetime filter
        end_time: Optional end datetime filter
        limit: Number of top users to return
        
    Returns:
        List of user focus statistics sorted by total focus time
    """
    if users is None:
        users = User.objects.all()
    
    leaderboard = []
    
    for user in users:
        total_duration = FocusLog.get_user_focus_duration(user, start_time, end_time)
        if total_duration > 0:  # Only include users with focus time
            total_sessions = FocusLog.objects.filter(
                user=user,
                event_type='focus_start'
            )
            
            if start_time:
                total_sessions = total_sessions.filter(timestamp__gte=start_time)
            if end_time:
                total_sessions = total_sessions.filter(timestamp__lte=end_time)
                
            total_sessions = total_sessions.count()
            
            leaderboard.append({
                'user': user,
                'username': user.username,
                'total_focus_duration': total_duration,
                'total_focus_duration_formatted': format_duration(total_duration),
                'total_sessions': total_sessions,
                'average_session_duration': total_duration / total_sessions if total_sessions > 0 else 0
            })
    
    # Sort by total focus duration (descending)
    leaderboard.sort(key=lambda x: x['total_focus_duration'], reverse=True)
    
    return leaderboard[:limit]