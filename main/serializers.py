from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, CarModel, ChatRoom, ChatMessage


class CarModelSerializer(serializers.ModelSerializer):
    """Serializer for car model catalog."""
    
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CarModel
        fields = ['id', 'name', 'image', 'image_url']
    
    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    car_model = CarModelSerializer(read_only=True)
    car_model_id = serializers.PrimaryKeyRelatedField(
        source='car_model',
        queryset=CarModel.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        write_only=True,
    )
    
    class Meta:
        model = User
        fields = [
            'id',
            'phone_number',
            'full_name',
            'phone_number_2',
            'car_model',
            'car_model_id',
            'car_plate_number',
            'instagram',
            'telegram',
            'whatsapp',
            'is_profile_public',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating User profile after QR scan."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=6,
        help_text='Password for account access'
    )
    car_model_id = serializers.PrimaryKeyRelatedField(
        source='car_model',
        queryset=CarModel.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        write_only=True,
    )
    
    class Meta:
        model = User
        fields = [
            'full_name',
            'phone_number',
            'phone_number_2',
            'car_model_id',
            'car_plate_number',
            'instagram',
            'telegram',
            'whatsapp',
            'is_profile_public',
            'password',
        ]
    
    def update(self, instance, validated_data):
        # Set password if provided
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        return super().update(instance, validated_data)


class UserCreateByUUIDSerializer(serializers.Serializer):
    """Serializer for creating/updating user by UUID after QR scan."""
    
    user_id = serializers.UUIDField(required=True)
    phone_number = serializers.CharField(required=True, max_length=20)
    password = serializers.CharField(required=True, write_only=True, min_length=6)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    phone_number_2 = serializers.CharField(required=False, allow_blank=True, max_length=20)
    car_model_id = serializers.UUIDField(required=False, allow_null=True)
    car_plate_number = serializers.CharField(required=False, allow_blank=True, max_length=50)
    instagram = serializers.CharField(required=False, allow_blank=True, max_length=255)
    telegram = serializers.CharField(required=False, allow_blank=True, max_length=255)
    whatsapp = serializers.CharField(required=False, allow_blank=True, max_length=255)
    is_profile_public = serializers.BooleanField(required=False)
    
    def validate_user_id(self, value):
        """Check if user with this UUID exists."""
        try:
            self.user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this UUID does not exist.")
        
        if self.user.phone_number:
            raise serializers.ValidationError("User already registered. Please login.")
        return value
    
    def validate_phone_number(self, value):
        """Check if phone number is already taken by another user."""
        if User.objects.filter(phone_number=value).exclude(id=self.initial_data.get('user_id')).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value
    
    def validate_car_model_id(self, value):
        if value is None:
            return value
        if not CarModel.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Car model not found.")
        return value
    
    def save(self):
        """Update the user with provided data."""
        user = User.objects.get(id=self.validated_data['user_id'])
        
        user.phone_number = self.validated_data['phone_number']
        user.full_name = self.validated_data.get('full_name', '')
        user.phone_number_2 = self.validated_data.get('phone_number_2', '')
        if 'car_model_id' in self.validated_data:
            user.car_model_id = self.validated_data.get('car_model_id')
        user.car_plate_number = self.validated_data.get('car_plate_number', '')
        user.instagram = self.validated_data.get('instagram', '')
        user.telegram = self.validated_data.get('telegram', '')
        user.whatsapp = self.validated_data.get('whatsapp', '')
        if 'is_profile_public' in self.validated_data:
            user.is_profile_public = self.validated_data['is_profile_public']
        
        user.set_password(self.validated_data['password'])
        user.save()
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login with phone number and password."""
    
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'phone_number': 'User with this phone number does not exist.'
            })
        
        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': 'Invalid password.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'phone_number': 'This account is disabled.'
            })
        
        attrs['user'] = user
        return attrs
    
    def get_tokens(self, user):
        """Generate JWT tokens for the user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""
    
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserSerializer()


class ChatStartSerializer(serializers.Serializer):
    """Serializer for starting a chat room from QR scan."""
    
    user_id = serializers.UUIDField(required=True)
    visitor_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    room_id = serializers.UUIDField(required=False)
    visitor_token = serializers.UUIDField(required=False)


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for chat room listing."""
    
    owner_id = serializers.UUIDField(source='owner.id', read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id',
            'owner_id',
            'visitor_name',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'owner_id', 'created_at', 'updated_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    
    room_id = serializers.UUIDField(source='room.id', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'room_id',
            'sender_type',
            'content',
            'created_at',
        ]
        read_only_fields = ['id', 'room_id', 'created_at']
