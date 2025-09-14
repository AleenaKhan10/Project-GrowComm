from django.urls import path
from . import views

app_name = 'audittrack'

urlpatterns = [
    # Dashboard view
    path('', views.audit_dashboard, name='dashboard'),
    
    # Test pages
    path('focus-test/', views.focus_test_page, name='focus_test'),
    
    # API endpoints - Audit logs
    path('api/statistics/', views.get_audit_statistics, name='statistics'),
    path('api/logs/', views.get_audit_logs, name='logs'),
    path('api/create/', views.create_audit_log, name='create_log'),
    
    # API endpoints - Focus tracking
    path('api/focus/log/', views.log_focus_event, name='log_focus'),
    path('api/focus/statistics/', views.get_focus_statistics, name='focus_statistics'),
    path('api/focus/logs/', views.get_focus_logs, name='focus_logs'),
]