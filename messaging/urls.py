from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Main inbox view
    path('', views.inbox, name='inbox'),
    
    # Conversation views
    path('conversation/<int:user_id>/', views.conversation_view, name='conversation'),
    
    # AJAX endpoints for messaging
    path('api/send/', views.send_message, name='send_message'),
    path('api/messages/<int:user_id>/', views.get_messages, name='get_messages'),
    path('api/mark-read/<int:message_id>/', views.mark_as_read, name='mark_as_read'),
    path('api/unread-count/', views.unread_count, name='unread_count'),
    path('api/search-users/', views.search_users, name='search_users'),
    
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
]