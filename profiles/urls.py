from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('view/<int:user_id>/', views.profile_view, name='view'),
    path('edit/', views.profile_edit, name='edit'),
    path('search/', views.user_search, name='search'),
]