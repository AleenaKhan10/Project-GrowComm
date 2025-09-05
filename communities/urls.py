from django.urls import path
from . import views

app_name = 'communities'

urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('send-message/', views.send_inline_message, name='send_inline_message'),
    path('communities/', views.community_list, name='community_list'),
    path('communities/<int:community_id>/', views.community_detail, name='community_detail'),
    path('communities/<int:community_id>/join/', views.join_community, name='join_community'),
    path('communities/<int:community_id>/leave/', views.leave_community, name='leave_community'),
]