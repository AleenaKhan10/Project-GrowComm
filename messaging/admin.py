from django.contrib import admin
from .models import MessageType, Conversation, Message, MessageRequest, UserMessageSettings, MessageReport, UserBlock, ChatBlock


@admin.register(MessageType)
class MessageTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'color_code')
    list_filter = ('is_active',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'created_date', 'last_message_date', 'is_active')
    list_filter = ('is_active', 'created_date')
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'timestamp', 'is_read')
    list_filter = ('message_type', 'is_read', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')
    readonly_fields = ('timestamp', 'read_date')


@admin.register(MessageRequest)
class MessageRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'message_type', 'status', 'created_date')
    list_filter = ('status', 'message_type', 'created_date')
    search_fields = ('from_user__username', 'to_user__username')


@admin.register(UserMessageSettings)
class UserMessageSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'coffee_chat_enabled', 'mentorship_enabled', 'networking_enabled', 'general_enabled')
    list_filter = ('coffee_chat_enabled', 'mentorship_enabled', 'networking_enabled', 'general_enabled')
    search_fields = ('user__username',)


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'report_type', 'created_date')
    list_filter = ('report_type', 'created_date')
    search_fields = ('reporter__username', 'reported_user__username', 'note')
    readonly_fields = ('created_date',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reporter', 'reported_user')


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_date')
    list_filter = ('created_date',)
    search_fields = ('blocker__username', 'blocked__username')
    readonly_fields = ('created_date',)


@admin.register(ChatBlock)
class ChatBlockAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'blocked_user', 'report_type', 'is_active', 'reviewed_by_admin', 'created_date')
    list_filter = ('is_active', 'reviewed_by_admin', 'created_date', 'report__report_type')
    search_fields = ('reporter__username', 'blocked_user__username', 'report__note', 'admin_notes')
    readonly_fields = ('created_date', 'updated_date')
    
    def report_type(self, obj):
        return obj.report.get_report_type_display()
    report_type.short_description = 'Report Type'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reporter', 'blocked_user', 'report')
