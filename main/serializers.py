from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = [
            'id',
            'phone_number',
            'full_name',
            'phone_number_2',
            'car_model',
            'car_plate_number',
            'instagram',
            'telegram',
            'whatsapp',
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
    
    class Meta:
        model = User
        fields = [
            'full_name',
            'phone_number',
            'phone_number_2',
            'car_model',
            'car_plate_number',
            'instagram',
            'telegram',
            'whatsapp',
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
    car_model = serializers.CharField(required=False, allow_blank=True, max_length=255)
    car_plate_number = serializers.CharField(required=False, allow_blank=True, max_length=50)
    instagram = serializers.CharField(required=False, allow_blank=True, max_length=255)
    telegram = serializers.CharField(required=False, allow_blank=True, max_length=255)
    whatsapp = serializers.CharField(required=False, allow_blank=True, max_length=255)
    
    def validate_user_id(self, value):
        """Check if user with this UUID exists."""
        try:
            self.user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this UUID does not exist.")
        return value
    
    def validate_phone_number(self, value):
        """Check if phone number is already taken by another user."""
        if User.objects.filter(phone_number=value).exclude(id=self.initial_data.get('user_id')).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value
    
    def save(self):
        """Update the user with provided data."""
        user = User.objects.get(id=self.validated_data['user_id'])
        
        user.phone_number = self.validated_data['phone_number']
        user.full_name = self.validated_data.get('full_name', '')
        user.phone_number_2 = self.validated_data.get('phone_number_2', '')
        user.car_model = self.validated_data.get('car_model', '')
        user.car_plate_number = self.validated_data.get('car_plate_number', '')
        user.instagram = self.validated_data.get('instagram', '')
        user.telegram = self.validated_data.get('telegram', '')
        user.whatsapp = self.validated_data.get('whatsapp', '')
        
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
