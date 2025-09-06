from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('view/<int:user_id>/', views.profile_view, name='view'),
    path('edit/', views.profile_edit, name='edit'),
    path('search/', views.user_search, name='search'),
    path('referrals/', views.referrals_view, name='referrals'),
    path('send-referral/', views.send_referral, name='send_referral'),
    path('referral-stats/', views.referral_stats, name='referral_stats'),
    path('delete/', views.delete_profile, name='delete'),
    # Custom message slot management URLs
    path('slots/add/', views.add_custom_slot, name='add_custom_slot'),
    path('slots/edit/<int:slot_id>/', views.edit_custom_slot, name='edit_custom_slot'),
    path('slots/delete/<int:slot_id>/', views.delete_custom_slot, name='delete_custom_slot'),
    path('slots/list/', views.get_custom_slots, name='get_custom_slots'),
]