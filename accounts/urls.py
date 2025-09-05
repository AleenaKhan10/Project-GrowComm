from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_choice_view, name='login'),
    path('login/admin/', views.AdminLoginView.as_view(), name='admin_login'),
    path('login/user/', views.UserLoginView.as_view(), name='user_login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('register/<uuid:invite_code>/', views.register_view, name='register'),
]