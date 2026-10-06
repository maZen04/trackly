from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='user-register'),
    path('login/', views.LoginView.as_view(), name='user-login'),
    path('refresh/', views.RefreshTokenView.as_view(), name='refresh'),
    path('logout/', views.LogoutView.as_view(), name='user-logout'),
]