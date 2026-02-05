import io
import base64
from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
import qrcode
from .models import User, ChatRoom, ChatMessage


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin configuration for User model with QR code generation."""
    
    list_display = [
        'id',
        'phone_number',
        'full_name',
        'car_model',
        'car_plate_number',
        'is_active',
        'is_profile_public',
        'created_at',
        'qr_codes_button',
    ]
    
    list_filter = [
        'is_active',
        'is_staff',
        'is_profile_public',
        'created_at',
    ]
    
    search_fields = [
        'id',
        'phone_number',
        'full_name',
        'car_plate_number',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('id', 'phone_number', 'full_name')
        }),
        (_('Phone Numbers'), {
            'fields': ('phone_number_2',)
        }),
        (_('Car Information'), {
            'fields': ('car_model', 'car_plate_number')
        }),
        (_('Social Media'), {
            'fields': ('instagram', 'telegram', 'whatsapp')
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_profile_public', 'is_staff', 'is_superuser')
        }),
        (_('Security'), {
            'fields': ('password',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Disable default add view
    def add_view(self, request, form_url='', extra_context=None):
        """Override add view to immediately create empty user and show QR codes."""
        # Create empty user with just UUID
        user = User.objects.create()
        
        # Show success message
        messages.success(request, _('Empty user created successfully. QR codes generated below.'))
        
        # Redirect to QR codes page for the new user
        return HttpResponseRedirect(
            reverse('admin:user-qr-codes', kwargs={'user_id': user.id})
        )
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override change view to handle empty users."""
        return super().change_view(request, object_id, form_url, extra_context)
    
    def qr_codes_button(self, obj):
        """Display a button to view QR codes."""
        return format_html(
            '<a class="button" href="{}">{}</a>',
            f'../user/{obj.id}/qr-codes/',
            _('View QR Codes')
        )
    qr_codes_button.short_description = _('QR Codes')
    qr_codes_button.allow_tags = True
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:user_id>/qr-codes/',
                self.admin_site.admin_view(self.qr_codes_view),
                name='user-qr-codes',
            ),
        ]
        return custom_urls + urls
    
    def generate_qr_code(self, data):
        """Generate QR code as base64 image."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return img_str
    
    def qr_codes_view(self, request, user_id):
        """View to display QR codes for a user."""
        user = User.objects.get(id=user_id)
        
        # Generate QR code with UUID
        uuid_qr = self.generate_qr_code(str(user.id))
        
        # Generate QR code with profile URL
        profile_url = user.get_profile_url()
        url_qr = self.generate_qr_code(profile_url)
        
        context = {
            **self.admin_site.each_context(request),
            'title': f'QR Codes for User',
            'user': user,
            'uuid_qr': uuid_qr,
            'url_qr': url_qr,
            'profile_url': profile_url,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/user_qr_codes.html', context)
    
    actions = ['generate_qr_codes_action']
    
    @admin.action(description=_('Generate QR codes for selected users'))
    def generate_qr_codes_action(self, request, queryset):
        """Action to generate QR codes for multiple users."""
        if queryset.count() == 1:
            user = queryset.first()
            from django.shortcuts import redirect
            return redirect(f'../user/{user.id}/qr-codes/')
        
        self.message_user(
            request,
            _('Please select only one user to generate QR codes.'),
            level='warning'
        )


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin configuration for chat rooms."""
    
    list_display = [
        'id',
        'owner',
        'visitor_name',
        'is_active',
        'created_at',
        'updated_at',
    ]
    
    list_filter = [
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'id',
        'owner__phone_number',
        'owner__full_name',
        'visitor_name',
    ]
    
    readonly_fields = [
        'id',
        'visitor_token',
        'created_at',
        'updated_at',
    ]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin configuration for chat messages."""
    
    list_display = [
        'id',
        'room',
        'sender_type',
        'sender',
        'short_content',
        'created_at',
    ]
    
    list_filter = [
        'sender_type',
        'created_at',
    ]
    
    search_fields = [
        'content',
        'room__id',
        'sender__phone_number',
        'sender__full_name',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
    ]
    
    def short_content(self, obj):
        return (obj.content[:40] + '...') if len(obj.content) > 40 else obj.content
    
    short_content.short_description = _('Content')
