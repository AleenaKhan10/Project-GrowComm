from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    # Non-community profile URLs (direct access)
    path('view/<int:user_id>/', views.profile_view, name='view'),
    path('edit/', views.profile_edit, name='edit'),
    path('delete/', views.delete_profile, name='delete'),
    path('search/', views.user_search, name='search'),
    path('referrals/', views.referrals_view, name='referrals'),
    path('send-referral/', views.send_referral, name='send_referral'),
    path('referral-stats/', views.referral_stats, name='referral_stats'),
    # Message categories management
    path('message-categories/', views.message_categories, name='message_categories'),
    # Custom message slot management URLs
    path('slots/add/', views.add_custom_slot, name='add_custom_slot'),
    path('slots/edit/<int:slot_id>/', views.edit_custom_slot, name='edit_custom_slot'),
    path('slots/delete/<int:slot_id>/', views.delete_custom_slot, name='delete_custom_slot'),
    path('slots/list/', views.get_custom_slots, name='get_custom_slots'),
    
    # Community-specific profile URLs
    path('community/<int:community_id>/view/<int:user_id>/', views.community_profile_view, name='community_view'),
    path('community/<int:community_id>/edit/', views.community_profile_edit, name='community_edit'),
    path('community/<int:community_id>/search/', views.community_user_search, name='community_search'),
    path('community/<int:community_id>/referrals/', views.community_referrals_view, name='community_referrals'),
    path('community/<int:community_id>/send-referral/', views.community_send_referral, name='community_send_referral'),
    path('community/<int:community_id>/referral-stats/', views.community_referral_stats, name='community_referral_stats'),
    path('community/<int:community_id>/message-categories/', views.community_message_categories, name='community_message_categories'),
    path('community/<int:community_id>/slots/add/', views.community_add_custom_slot, name='community_add_custom_slot'),
    path('community/<int:community_id>/slots/edit/<int:slot_id>/', views.community_edit_custom_slot, name='community_edit_custom_slot'),
    path('community/<int:community_id>/slots/delete/<int:slot_id>/', views.community_delete_custom_slot, name='community_delete_custom_slot'),
    path('community/<int:community_id>/slots/list/', views.community_get_custom_slots, name='community_get_custom_slots'),
]