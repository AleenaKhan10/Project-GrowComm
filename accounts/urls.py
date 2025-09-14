from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Primary login URL
    path('login/', views.UnifiedLoginView.as_view(), name='login'),
    
    # Legacy URLs for backward compatibility
    path('unified-login/', views.UnifiedLoginView.as_view(), name='unified_login'),
    path('login/admin/', views.AdminLoginView.as_view(), name='admin_login'),
    path('login/user/', views.UserLoginView.as_view(), name='user_login'),
    
    # Authentication flows
    path('logout/', views.logout_view, name='logout'),
    path('register/<uuid:invite_code>/', views.register_view, name='register'),
    path('verify-otp/<str:email>/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    
    # Password reset
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/confirm/<str:token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
]