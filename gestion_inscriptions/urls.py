# urls.py - Updated with authentication URLs

from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('auth/', views.auth_view, name='auth'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/signup/', views.signup_view, name='signup'),
    path('auth/logout/', views.logout_view, name='logout'),
    
    # Existing URLs (now protected)
    path('', views.etape1_view, name='etape1'),  
    path('etape2/', views.etape2_view, name='etape2'),
    path('confirmation/', views.confirmation_view, name='confirmation'),
]