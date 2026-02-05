from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from .models import User, ChatRoom
from .serializers import (
    UserSerializer,
    UserCreateByUUIDSerializer,
    LoginSerializer,
    TokenResponseSerializer,
    ChatStartSerializer,
    ChatRoomSerializer,
    ChatMessageSerializer,
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
        user = get_object_or_404(User, id=user_id, is_profile_public=True)
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
        users = User.objects.filter(is_active=True, is_profile_public=True)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class ChatStartAPIView(APIView):
    """
    API view to start a chat room after QR scan.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Start chat by user UUID",
        description="Create a chat room for a visitor and return room_id + visitor_token.",
        request=ChatStartSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "visitor_token": {"type": "string"},
                        "ws_path": {"type": "string"},
                    }
                },
                description="Chat room created"
            ),
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="User not found"),
        },
        tags=["Chat"],
    )
    def post(self, request):
        serializer = ChatStartSerializer(data=request.data)
        if serializer.is_valid():
            owner = get_object_or_404(User, id=serializer.validated_data['user_id'], is_active=True)
            room = ChatRoom.objects.create(
                owner=owner,
                visitor_name=serializer.validated_data.get('visitor_name', '')
            )
            return Response({
                'room_id': str(room.id),
                'visitor_token': str(room.visitor_token),
                'ws_path': f"/ws/chat/{room.id}/",
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatRoomListAPIView(APIView):
    """
    API view to list chat rooms for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List chat rooms",
        description="Get chat rooms for the authenticated user.",
        responses={
            200: OpenApiResponse(response=ChatRoomSerializer(many=True), description="Chat rooms"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Chat"],
    )
    def get(self, request):
        rooms = ChatRoom.objects.filter(owner=request.user).order_by('-updated_at')
        serializer = ChatRoomSerializer(rooms, many=True)
        return Response(serializer.data)


class ChatMessageListAPIView(APIView):
    """
    API view to list messages for a chat room.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="List chat messages",
        description="Get messages for a chat room. Owner uses JWT; visitor uses visitor token.",
        parameters=[
            OpenApiParameter(
                name="room_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Chat room UUID",
                required=True,
            ),
            OpenApiParameter(
                name="visitor",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Visitor token (required for anonymous visitor)",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(response=ChatMessageSerializer(many=True), description="Messages"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not allowed"),
            404: OpenApiResponse(description="Room not found"),
        },
        tags=["Chat"],
    )
    def get(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id, is_active=True)
        
        if request.user.is_authenticated and request.user == room.owner:
            allowed = True
        else:
            visitor_token = request.query_params.get('visitor')
            allowed = visitor_token and visitor_token == str(room.visitor_token)
        
        if not allowed:
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        
        messages = room.messages.order_by('created_at')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
