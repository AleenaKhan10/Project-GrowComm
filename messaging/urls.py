from django.urls import path
from . import views
from . import community_views

app_name = 'messaging'

urlpatterns = [
    # Main inbox view (no community context)
    path('', views.inbox, name='inbox'),
    
    # Community-specific messaging
    path('community/<int:community_id>/', community_views.community_inbox, name='community_inbox'),
    path('community/<int:community_id>/conversation/<int:user_id>/', community_views.community_conversation_view, name='community_conversation'),
    path('community/<int:community_id>/send-request/<int:user_id>/', community_views.community_send_message_request, name='community_send_request'),
    path('community/<int:community_id>/api/send-message/', community_views.community_send_message_api, name='community_send_message_api'),
    
    # Non-community conversation views
    path('conversation/<int:user_id>/', views.conversation_view, name='conversation'),
    
    # AJAX endpoints for messaging
    path('api/send/', views.send_message, name='send_message'),
    path('api/messages/<int:user_id>/', views.get_messages, name='get_messages'),
    path('api/mark-read/<int:message_id>/', views.mark_as_read, name='mark_as_read'),
    path('api/unread-count/', views.unread_count, name='unread_count'),
    path('api/search-users/', views.search_users, name='search_users'),
    path('api/reveal-identity/<int:user_id>/', views.reveal_identity, name='reveal_identity'),
    
    # Report and Block endpoints
    path('api/report/<int:user_id>/', views.report_user, name='report_user'),
    path('api/block/<int:user_id>/', views.block_user, name='block_user'),
    path('api/unblock/<int:user_id>/', views.unblock_chat, name='unblock_chat'),
    path('blocked-users/', views.blocked_users, name='blocked_users'),
    
    # Message requests (kept for backward compatibility)
    path('requests/', views.message_requests, name='message_requests'),
    path('requests/sent/', views.sent_requests, name='sent_requests'),
    path('requests/<int:request_id>/respond/', views.respond_to_request, name='respond_to_request'),
    path('send-request/<int:user_id>/', views.send_message_request, name='send_request'),
    
    # Settings
    path('settings/', views.message_settings, name='settings'),
    
    # Legacy URLs for backward compatibility
    path('conversation/detail/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversation/<int:conversation_id>/messages/', views.get_conversation_messages, name='conversation_messages'),
    path('conversation/<int:conversation_id>/reply/', views.send_conversation_reply, name='conversation_reply'),
    
    
    # Admin URLs for user management
    path('admin/users/', views.admin_users_list, name='admin_users_list'),
    path('admin/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/suspend/', views.admin_suspend_user, name='admin_suspend_user'),
    path('admin/users/<int:user_id>/unsuspend/', views.admin_unsuspend_user, name='admin_unsuspend_user'),
    path('admin/users/<int:user_id>/restore/', views.admin_restore_user, name='admin_restore_user'),
    
    # Admin URLs for credit management
    path('admin/credits/', views.admin_credit_management, name='admin_credit_management'),
    path('admin/credits/reset/<int:user_id>/', views.admin_reset_user_credits, name='admin_reset_user_credits'),
    
    # Chat heading management
    path('api/chat-heading/<int:user_id>/', views.chat_heading_api, name='chat_heading_api'),
    
    # User info API
    path('api/user-info/<int:user_id>/', views.user_info_api, name='user_info_api'),
]