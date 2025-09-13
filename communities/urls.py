from django.urls import path
from . import views

app_name = 'communities'

urlpatterns = [
    # Community selection (no community context)
    path('communities/', views.community_list, name='community_list'),
    path('communities/<int:community_id>/', views.community_detail, name='community_detail'),
    path('communities/<int:community_id>/join/', views.join_community, name='join_community'),
    path('communities/<int:community_id>/leave/', views.leave_community, name='leave_community'),
    
    # Community-specific pages (require community membership)
    path('community/<int:community_id>/', views.user_list, name='user_list'),
    path('community/<int:community_id>/user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('community/<int:community_id>/send-message/', views.send_inline_message, name='send_inline_message'),
    
    # Admin routes
    path('admin/communities/', views.admin_community_list, name='admin_community_list'),
    path('admin/communities/create/', views.admin_community_create, name='admin_community_create'),
    path('admin/communities/<int:community_id>/edit/', views.admin_community_edit, name='admin_community_edit'),
]