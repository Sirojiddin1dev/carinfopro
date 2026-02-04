from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from .views import (
    UserDetailAPIView,
    UserCreateByUUIDAPIView,
    LoginAPIView,
    UserProfileAPIView,
    UserListAPIView,
)

urlpatterns = [
    # Swagger/OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Redoc UI (alternative)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # User list
    path('api/users/', UserListAPIView.as_view(), name='user-list'),
    
    # Public user profile by UUID
    path('user/<uuid:user_id>/', UserDetailAPIView.as_view(), name='user-detail'),
    
    # User registration/update after QR scan
    path('api/user/register/', UserCreateByUUIDAPIView.as_view(), name='user-register'),
    
    # Login
    path('api/login/', LoginAPIView.as_view(), name='user-login'),
    
    # Token refresh
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Current user profile (requires authentication)
    path('api/profile/', UserProfileAPIView.as_view(), name='user-profile'),
]
