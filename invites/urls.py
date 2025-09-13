from django.urls import path
from . import views
from . import community_views

app_name = 'invites'

urlpatterns = [
    # Non-community invites URLs
    path('', views.my_invites, name='my_invites'),
    path('<int:invite_id>/', views.invite_detail, name='invite_detail'),
    path('referrals/', views.referral_status, name='referral_status'),
    
    # Community-specific invites URLs
    path('community/<int:community_id>/', community_views.community_my_invites, name='community_my_invites'),
    path('community/<int:community_id>/<int:invite_id>/', community_views.community_invite_detail, name='community_invite_detail'),
    path('community/<int:community_id>/referrals/', community_views.community_referral_status, name='community_referral_status'),
]