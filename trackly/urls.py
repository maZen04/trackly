from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='token_obtain_pair'),
    path('login/', views.LoginView.as_view(), name='token_refresh'),
    path('refresh/', views.RefreshTokenView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='token_refresh'),
]