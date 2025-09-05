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
]