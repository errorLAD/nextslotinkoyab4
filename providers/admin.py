"""
Admin configuration for Provider models.
Enhanced with custom actions, filters, and inline editing.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import ServiceProvider, Service, Testimonial, HeroImage, TeamMember


class ServiceInline(admin.TabularInline):
    """Inline editing for services within provider admin."""
    model = Service
    extra = 1
    fields = ['service_name', 'price', 'duration_minutes', 'is_active']
    show_change_link = True


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = [
        'business_name', 'user_email', 'business_type', 'city', 
        'plan_badge', 'subscription_status', 'appointments_this_month',
        'is_verified', 'is_active', 'created_at'
    ]
    list_filter = [
        'business_type', 'current_plan', 'is_verified', 
        'is_active', 'city', 'state'
    ]
    search_fields = ['business_name', 'user__email', 'phone', 'city', 'unique_booking_url']
    readonly_fields = [
        'created_at', 'updated_at', 'last_reset_date', 
        'plan_status_display', 'booking_link'
    ]
    
    # Inline editing
    inlines = [ServiceInline]
    
    # Custom actions
    actions = [
        'activate_providers', 
        'deactivate_providers', 
        'verify_providers',
        'upgrade_to_pro',
        'reset_appointment_counter'
    ]
    
    fieldsets = (
        ('User & Business Info', {
            'fields': ('user', 'business_name', 'business_type', 'description', 'booking_link')
        }),
        ('Contact Information', {
            'fields': ('phone', 'whatsapp_number', 'business_address', 'city', 'state', 'pincode')
        }),
        ('Subscription Plan', {
            'fields': (
                'current_plan', 'plan_status_display', 'plan_start_date', 'plan_end_date'
            )
        }),
        ('Usage Tracking', {
            'fields': ('appointments_this_month', 'last_reset_date')
        }),
        ('Booking Configuration', {
            'fields': ('unique_booking_url', 'profile_image')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    # Custom display methods
    def user_email(self, obj):
        """Display user email with link to user admin."""
        url = reverse('admin:accounts_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def plan_badge(self, obj):
        """Display plan with colored badge."""
        if obj.current_plan == 'pro':
            return format_html(
                '<span style="background-color: #4f46e5; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">PRO</span>'
            )
        return format_html(
            '<span style="background-color: #6b7280; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">FREE</span>'
        )
    plan_badge.short_description = 'Plan'
    
    def subscription_status(self, obj):
        """Display subscription status with icon."""
        if obj.current_plan == 'free':
            return '✅ Active (Free)'
        elif obj.plan_end_date:
            days_left = (obj.plan_end_date - timezone.now().date()).days
            if days_left < 0:
                return format_html('<span style="color: red;">❌ Expired</span>')
            elif days_left <= 3:
                return format_html('<span style="color: orange;">⚠️ Expires in {} days</span>', days_left)
            else:
                return f'✅ Active ({days_left} days left)'
        return '✅ Active'
    subscription_status.short_description = 'Status'
    
    def plan_status_display(self, obj):
        """Detailed plan status for detail view."""
        if obj.current_plan == 'pro':
            if obj.plan_end_date:
                days_left = (obj.plan_end_date - timezone.now().date()).days
                return f"PRO Plan - {days_left} days remaining"
            return "PRO Plan - Active"
        else:
            remaining = obj.remaining_appointments()
            return f"FREE Plan - {remaining} appointments remaining this month"
    plan_status_display.short_description = 'Plan Status'
    
    def booking_link(self, obj):
        """Display booking page link."""
        from django.conf import settings
        url = f"{settings.SITE_URL}/book/{obj.unique_booking_url}/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
    booking_link.short_description = 'Booking Page'
    
    # Custom actions
    def activate_providers(self, request, queryset):
        """Activate selected providers."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} provider(s) activated successfully.')
    activate_providers.short_description = 'Activate selected providers'
    
    def deactivate_providers(self, request, queryset):
        """Deactivate selected providers."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} provider(s) deactivated successfully.')
    deactivate_providers.short_description = 'Deactivate selected providers'
    
    def verify_providers(self, request, queryset):
        """Verify selected providers."""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} provider(s) verified successfully.')
    verify_providers.short_description = 'Verify selected providers'
    
    def upgrade_to_pro(self, request, queryset):
        """Upgrade selected providers to PRO plan (1 month)."""
        count = 0
        for provider in queryset:
            provider.upgrade_to_pro(duration_months=1)
            count += 1
        self.message_user(request, f'{count} provider(s) upgraded to PRO plan.')
    upgrade_to_pro.short_description = 'Upgrade to PRO (1 month)'
    
    def reset_appointment_counter(self, request, queryset):
        """Reset monthly appointment counter for FREE plan providers."""
        count = 0
        for provider in queryset.filter(current_plan='free'):
            provider.reset_monthly_counter()
            count += 1
        self.message_user(request, f'Reset appointment counter for {count} FREE plan provider(s).')
    reset_appointment_counter.short_description = 'Reset appointment counter (FREE plan)'


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['service_name', 'service_provider', 'price', 'duration_minutes', 'is_active', 'created_at']
    list_filter = ['is_active', 'duration_minutes']
    search_fields = ['service_name', 'service_provider__business_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
            ('Service Information', {
                'fields': ('service_provider', 'service_name', 'description')
            }),
            ('Pricing & Duration', {
                'fields': ('price', 'duration_minutes')
            }),
            ('Status', {
                'fields': ('is_active',)
            }),
            ('Timestamps', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'service_provider', 'rating', 'is_featured', 'is_active', 'date_added']
    list_filter = ['rating', 'is_featured', 'is_active', 'date_added']
    search_fields = ['client_name', 'service_provider__business_name', 'testimonial_text']
    readonly_fields = ['date_added']
    fieldsets = (
        ('Testimonial Information', {
            'fields': ('service_provider', 'client_name', 'client_photo', 'testimonial_text', 'rating')
        }),
        ('Display Options', {
            'fields': ('is_featured', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('date_added',),
            'classes': ('collapse',)
        }),
    )


@admin.register(HeroImage)
class HeroImageAdmin(admin.ModelAdmin):
    list_display = ['service_provider', 'display_order', 'is_active', 'image_preview']
    list_filter = ['is_active', 'service_provider']
    search_fields = ['service_provider__business_name', 'caption']
    fieldsets = (
        ('Image Information', {
            'fields': ('service_provider', 'image', 'caption')
        }),
        ('Display Options', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    def image_preview(self, obj):
        """Display image thumbnail in list view."""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 3px;" />',
                obj.image.url
            )
        return '—'
    image_preview.short_description = 'Preview'


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_provider', 'role_title', 'display_order', 'is_active', 'photo_preview']
    list_filter = ['is_active', 'service_provider']
    search_fields = ['name', 'role_title', 'service_provider__business_name']
    fieldsets = (
        ('Team Member Information', {
            'fields': ('service_provider', 'name', 'role_title', 'photo', 'bio')
        }),
        ('Professional Details', {
            'fields': ('specialties', 'credentials')
        }),
        ('Display Options', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    def photo_preview(self, obj):
        """Display photo thumbnail in list view."""
        if obj.photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 50%; border: 2px solid #ccc;" />',
                obj.photo.url
            )
        return '—'
    photo_preview.short_description = 'Photo'


# Availability admin removed
