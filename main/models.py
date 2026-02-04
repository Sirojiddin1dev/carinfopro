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
    car_model = models.CharField(
        max_length=255,
        blank=True,
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
        return f"https://carinfopro.uz/user/{self.id}"
