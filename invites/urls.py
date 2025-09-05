from django.urls import path
from . import views

app_name = 'invites'

urlpatterns = [
    path('', views.my_invites, name='my_invites'),
    path('<int:invite_id>/', views.invite_detail, name='invite_detail'),
    path('referrals/', views.referral_status, name='referral_status'),
]