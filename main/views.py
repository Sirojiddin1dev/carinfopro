from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from .models import User
from .serializers import (
    UserSerializer,
    UserCreateByUUIDSerializer,
    LoginSerializer,
    TokenResponseSerializer,
)


class UserDetailAPIView(APIView):
    """API view to get user details by UUID (public profile)."""
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get user by UUID",
        description="Get public user profile information by UUID.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User UUID (from QR code)",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(response=UserSerializer, description="User profile"),
            404: OpenApiResponse(description="User not found"),
        },
        tags=["Users"],
    )
    def get(self, request, user_id):
        """Get user public profile."""
        user = get_object_or_404(User, id=user_id)
        serializer = UserSerializer(user)
        return Response(serializer.data)


class UserCreateByUUIDAPIView(APIView):
    """
    API view to update user details after scanning QR code.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Register/Update user after QR scan",
        description="""
        Update user profile after scanning QR code with mobile app.
        
        Required fields:
        - user_id: UUID from QR code
        - phone_number: User's phone number
        - password: Account password
        
        Optional fields:
        - full_name, phone_number_2, car_model, car_plate_number
        - instagram, telegram, whatsapp
        """,
        request=UserCreateByUUIDSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "user": {"type": "object"},
                        "tokens": {
                            "type": "object",
                            "properties": {
                                "refresh": {"type": "string"},
                                "access": {"type": "string"},
                            }
                        }
                    }
                },
                description="User updated successfully with tokens"
            ),
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["Authentication"],
    )
    def post(self, request):
        """Update user profile after QR scan and create account."""
        serializer = UserCreateByUUIDSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'User profile updated successfully.',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    """
    API view for user login with phone number and password.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="User login",
        description="Login with phone number and password to get JWT tokens.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "tokens": {
                            "type": "object",
                            "properties": {
                                "refresh": {"type": "string"},
                                "access": {"type": "string"},
                            }
                        },
                        "user": {"type": "object"},
                    }
                },
                description="Login successful with tokens"
            ),
            400: OpenApiResponse(description="Invalid credentials"),
        },
        tags=["Authentication"],
    )
    def post(self, request):
        """Authenticate user and return JWT tokens."""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = serializer.get_tokens(user)
            
            return Response({
                'tokens': tokens,
                'user': UserSerializer(user).data,
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileAPIView(APIView):
    """
    API view to get/update current user profile.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get current user profile",
        description="Get the profile of the currently authenticated user.",
        responses={
            200: OpenApiResponse(response=UserSerializer, description="User profile"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Profile"],
    )
    def get(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Update current user profile",
        description="Update the profile of the currently authenticated user.",
        request=UserSerializer,
        responses={
            200: OpenApiResponse(response=UserSerializer, description="Updated profile"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Profile"],
    )
    def put(self, request):
        """Update current user profile."""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Partial update user profile",
        description="Partially update the profile of the currently authenticated user.",
        request=UserSerializer,
        responses={
            200: OpenApiResponse(response=UserSerializer, description="Updated profile"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Profile"],
    )
    def patch(self, request):
        """Partial update current user profile."""
        return self.put(request)


class UserListAPIView(APIView):
    """
    API view to list all users (for admin or public listing).
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="List all users",
        description="Get a list of all active users.",
        responses={
            200: OpenApiResponse(response=UserSerializer(many=True), description="List of users"),
        },
        tags=["Users"],
    )
    def get(self, request):
        """List all active users."""
        users = User.objects.filter(is_active=True)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
