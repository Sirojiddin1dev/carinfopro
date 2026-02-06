from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from .views import (
    UserCreateByUUIDAPIView,
    LoginAPIView,
    UserProfileAPIView,
    ChatStartAPIView,
    ChatRoomListAPIView,
    ChatMessageListAPIView,
)

urlpatterns = [
    # Swagger/OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Redoc UI (alternative)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # User registration/update after QR scan
    path('api/user/register/', UserCreateByUUIDAPIView.as_view(), name='user-register'),
    
    # Login
    path('api/login/', LoginAPIView.as_view(), name='user-login'),
    
    # Token refresh
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Current user profile (requires authentication)
    path('api/profile/', UserProfileAPIView.as_view(), name='user-profile'),
    
    # Chat
    path('api/chat/start/', ChatStartAPIView.as_view(), name='chat-start'),
    path('api/chat/rooms/', ChatRoomListAPIView.as_view(), name='chat-rooms'),
    path('api/chat/rooms/<uuid:room_id>/messages/', ChatMessageListAPIView.as_view(), name='chat-messages'),
]
