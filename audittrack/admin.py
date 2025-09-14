from django.contrib import admin
from django.utils.html import format_html
from .models import AuditEvent, FocusLog


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'action_detail', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'action_detail']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']


@admin.register(FocusLog)
class FocusLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'focus_event_icon', 'page_title_short', 'event_type', 'timestamp', 'session_id']
    list_filter = ['event_type', 'timestamp', 'user']
    search_fields = ['user__username', 'page_url', 'page_title', 'session_id']
    readonly_fields = ['timestamp', 'user_agent', 'ip_address']
    ordering = ['-timestamp']
    
    def focus_event_icon(self, obj):
        """Display icon for focus event type"""
        icon = "📍" if obj.event_type == 'focus_start' else "💤"
        color = "green" if obj.event_type == 'focus_start' else "orange"
        return format_html(
            '<span style="font-size: 16px; color: {};">{}</span>',
            color,
            icon
        )
    focus_event_icon.short_description = 'Event'
    focus_event_icon.admin_order_field = 'event_type'
    
    def page_title_short(self, obj):
        """Display shortened page title with full URL as tooltip"""
        title = obj.page_title or obj.page_url
        if len(title) > 50:
            title = title[:47] + "..."
        return format_html(
            '<span title="{}">{}</span>',
            obj.page_url,
            title
        )
    page_title_short.short_description = 'Page'
    page_title_short.admin_order_field = 'page_title'
    
    # Custom filters
    class EventTypeFilter(admin.SimpleListFilter):
        title = 'Focus Event'
        parameter_name = 'focus_event'
        
        def lookups(self, request, model_admin):
            return (
                ('focus_start', '📍 Focus Start'),
                ('focus_end', '💤 Focus End'),
            )
        
        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(event_type=self.value())
    
    list_filter = [EventTypeFilter, 'timestamp', 'user']
    
    # Add custom actions
    actions = ['mark_selected_sessions']
    
    def mark_selected_sessions(self, request, queryset):
        """Custom action to analyze selected focus sessions"""
        session_ids = queryset.values_list('session_id', flat=True).distinct()
        self.message_user(
            request,
            f"Selected logs contain {len(session_ids)} unique sessions from {queryset.count()} events."
        )
    mark_selected_sessions.short_description = "Analyze selected focus sessions"
    
    # Customize the admin form
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'event_type', 'timestamp')
        }),
        ('Page Details', {
            'fields': ('page_url', 'page_title')
        }),
        ('Session Info', {
            'fields': ('session_id', 'user_agent', 'ip_address'),
            'classes': ('collapse',)
        }),
    )
