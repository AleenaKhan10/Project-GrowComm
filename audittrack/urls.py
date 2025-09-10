from django.urls import path
from . import views

app_name = 'audittrack'

urlpatterns = [
    # Dashboard view
    path('', views.audit_dashboard, name='dashboard'),
    
    # API endpoints
    path('api/statistics/', views.get_audit_statistics, name='statistics'),
    path('api/logs/', views.get_audit_logs, name='logs'),
    path('api/create/', views.create_audit_log, name='create_log'),
]