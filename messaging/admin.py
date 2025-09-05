from django.contrib import admin
from .models import MessageType, Conversation, Message, MessageRequest, UserMessageSettings


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
