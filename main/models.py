import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for User model with phone number as username."""
    
    def create_user(self, phone_number=None, password=None, **extra_fields):
        # Allow creating user without phone_number (will be set later via QR)
        
        extra_fields.setdefault('is_active', True)
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(phone_number, password, **extra_fields)


class CarModel(models.Model):
    """Car model catalog."""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('UUID')
    )
    
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_('Name')
    )
    
    image = models.ImageField(
        upload_to='car_models/',
        blank=True,
        null=True,
        verbose_name=_('Image')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Car Model')
        verbose_name_plural = _('Car Models')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        image_changed = False
        if self.pk:
            old_image = CarModel.objects.filter(pk=self.pk).values_list('image', flat=True).first()
            old_image_name = old_image or ''
            new_image_name = self.image.name if self.image else ''
            image_changed = (old_image_name != new_image_name)
        else:
            image_changed = bool(self.image)
        
        super().save(*args, **kwargs)
        
        if image_changed and self.image:
            try:
                from main.image_compressor import compress_uploaded_image
                compress_uploaded_image(self.image)
            except Exception:
                pass


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with phone number as username field."""
    
    # Primary key - UUID
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('UUID')
    )
    
    # Phone number (used for login) - optional at creation, required later
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_('Phone Number')
    )
    
    # Full name
    full_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Full Name')
    )
    
    # Second phone number (optional)
    phone_number_2 = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Phone Number 2')
    )
    
    # Car information
    car_model = models.ForeignKey(
        CarModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Car Model')
    )
    
    car_plate_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Car Plate Number')
    )
    
    # Social media links
    instagram = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Instagram')
    )
    
    telegram = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Telegram')
    )
    
    whatsapp = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('WhatsApp')
    )
    
    # Status fields
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )

    # Profile visibility
    is_profile_public = models.BooleanField(
        default=True,
        verbose_name=_('Profile Public')
    )
    
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_('Staff Status')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    # Specify the username field
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.full_name or 'Unnamed'} ({self.phone_number})"
    
    def get_profile_url(self):
        """Returns the user profile URL."""
        return f"https://api.carinfopro.uz/user/{self.id}"


class ChatRoom(models.Model):
    """Chat room between a visitor and a user (car owner)."""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('UUID')
    )
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_rooms',
        verbose_name=_('Owner')
    )
    
    visitor_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Visitor Token')
    )
    
    visitor_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Visitor Name')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Chat Room')
        verbose_name_plural = _('Chat Rooms')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"ChatRoom {self.id} ({self.owner_id})"


class ChatMessage(models.Model):
    """Chat message in a room."""
    
    class SenderType(models.TextChoices):
        OWNER = 'owner', _('Owner')
        VISITOR = 'visitor', _('Visitor')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('UUID')
    )
    
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Room')
    )
    
    sender_type = models.CharField(
        max_length=10,
        choices=SenderType.choices,
        verbose_name=_('Sender Type')
    )
    
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_messages',
        verbose_name=_('Sender User')
    )
    
    content = models.TextField(
        verbose_name=_('Content')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    class Meta:
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender_type} message in {self.room_id}"
