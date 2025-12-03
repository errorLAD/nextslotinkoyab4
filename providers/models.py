"""
Models for Service Providers, Services, and Availability.
Includes freemium pricing model with usage tracking.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator
import uuid
import os

# Maximum staff members for PRO plan
MAX_STAFF_MEMBERS_PRO = 10


def sanitize_filename(filename):
    """
    Sanitize uploaded filenames by removing spaces and special characters.
    Converts spaces to hyphens, keeps only alphanumeric, hyphens, underscores, and dots.
    """
    if not filename:
        return filename
    
    name, ext = os.path.splitext(filename)
    # Replace spaces with hyphens
    name = name.replace(' ', '-')
    # Remove special characters, keep only alphanumeric, hyphens, underscores
    name = ''.join(c if c.isalnum() or c in '-_' else '' for c in name)
    # Limit filename length
    if len(name) > 50:
        name = name[:50]
    return name + ext.lower()


def upload_profile_image(instance, filename):
    """Upload handler for profile images."""
    filename = sanitize_filename(filename)
    # Use pk or uuid for unique naming
    instance_id = instance.pk or uuid.uuid4().hex[:8]
    return f'profile_images/{instance_id}_{filename}'


def upload_logo(instance, filename):
    """Upload handler for logos."""
    filename = sanitize_filename(filename)
    instance_id = instance.pk or uuid.uuid4().hex[:8]
    return f'provider_logos/{instance_id}_{filename}'


def upload_hero_image(instance, filename):
    """Upload handler for hero images."""
    filename = sanitize_filename(filename)
    provider_id = instance.service_provider_id or 'new'
    instance_id = instance.pk or uuid.uuid4().hex[:8]
    return f'hero_images/{provider_id}_{instance_id}_{filename}'


def upload_team_photo(instance, filename):
    """Upload handler for team photos."""
    filename = sanitize_filename(filename)
    provider_id = instance.service_provider_id or 'new'
    instance_id = instance.pk or uuid.uuid4().hex[:8]
    return f'team_photos/{provider_id}_{instance_id}_{filename}'


def upload_testimonial_photo(instance, filename):
    """Upload handler for testimonial photos."""
    filename = sanitize_filename(filename)
    provider_id = instance.service_provider_id or 'new'
    instance_id = instance.pk or uuid.uuid4().hex[:8]
    return f'testimonial_photos/{provider_id}_{instance_id}_{filename}'


class ServiceProvider(models.Model):
    """
    Service Provider profile with subscription plan management.
    One-to-One relationship with CustomUser.
    """
    
    BUSINESS_TYPE_CHOICES = [
        ('salon', 'Salon & Spa'),
        ('fitness', 'Fitness & Gym'),
        ('tutor', 'Tutoring & Education'),
        ('healthcare', 'Healthcare & Wellness'),
        ('other', 'Other Services'),
    ]
    
    PLAN_CHOICES = [
        ('free', 'Free Plan'),
        ('pro', 'Pro Plan'),
    ]
    
    # User relationship
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='provider_profile'
    )
    
    # Business Information
    business_name = models.CharField(
        max_length=200,
        help_text='Your business or professional name'
    )
    
    accepting_appointments = models.BooleanField(
        default=True,
        help_text='Whether this provider is currently accepting new appointments'
    )
    
    business_type = models.CharField(
        max_length=20,
        choices=BUSINESS_TYPE_CHOICES,
        default='other'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Brief description of your services'
    )
    
    # Contact Information
    phone = models.CharField(
        max_length=15,
        help_text='Primary contact number'
    )
    
    whatsapp_number = models.CharField(
        max_length=15,
        blank=True,
        help_text='WhatsApp number for notifications (Pro plan only)'
    )
    
    # Address
    business_address = models.TextField(
        blank=True,
        help_text='Full business address'
    )
    
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    
    # Domain Configuration
    custom_domain = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text='Custom domain or subdomain (e.g., ramesh-salon.yourdomain.com or www.rameshsalon.com)'
    )
    custom_domain_type = models.CharField(
        max_length=20,
        choices=[
            ('none', 'Default'),
            ('subdomain', 'Custom Subdomain'),
            ('domain', 'Custom Domain')
        ],
        default='none',
        help_text='Type of custom domain configuration'
    )
    domain_verified = models.BooleanField(
        default=False,
        help_text='Whether the domain has been verified'
    )
    domain_verification_code = models.CharField(
        max_length=100,
        blank=True,
        help_text='Random code for domain verification'
    )
    domain_added_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When the domain was added'
    )
    ssl_enabled = models.BooleanField(
        default=False,
        help_text='Whether SSL is enabled for the custom domain'
    )
    
    # Subscription & Plan Management
    current_plan = models.CharField(
        max_length=10,
        choices=PLAN_CHOICES,
        default='free',
        help_text='Current subscription plan'
    )
    
    plan_start_date = models.DateField(
        default=timezone.now,
        help_text='Date when current plan started'
    )
    
    plan_end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Plan expiry date (null for free plan or unlimited)'
    )
    
    # Removed trial-related fields as per requirements
    # Usage Tracking (for FREE plan limits)
    appointments_this_month = models.IntegerField(
        default=0,
        help_text='Number of appointments created this month'
    )
    
    last_reset_date = models.DateField(
        default=timezone.now,
        help_text='Last date when monthly counter was reset'
    )
    
    # Booking Configuration
    unique_booking_url = models.SlugField(
        max_length=100,
        unique=True,
        help_text='Unique URL slug for booking page (e.g., /book/your-salon)'
    )
    
    # Media
    profile_image = models.ImageField(
        upload_to=upload_profile_image,
        blank=True,
        null=True,
        help_text='Business logo or profile picture'
    )
    
    # Branding & About
    logo = models.ImageField(
        upload_to=upload_logo,
        blank=True,
        null=True,
        help_text='Upload your business logo (recommended: 500x500px square)'
    )
    
    mission_statement = models.TextField(
        blank=True,
        null=True,
        max_length=500,
        help_text='What is your business mission?'
    )
    
    vision_statement = models.TextField(
        blank=True,
        null=True,
        max_length=500,
        help_text='What is your long-term vision?'
    )
    
    about_us = models.TextField(
        blank=True,
        null=True,
        help_text='Tell clients about your business, history, values'
    )
    
    # Social Media Links
    instagram_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    
    # Branding & Customization
    hero_color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        default='#7c3aed',
        help_text='Hero section background color (hex format, e.g., #7c3aed)'
    )
    
    # Legal Policy Links
    terms_conditions_url = models.URLField(
        blank=True,
        null=True,
        help_text='Link to your Terms & Conditions (can be external like Notion, Google Docs)'
    )
    privacy_policy_url = models.URLField(
        blank=True,
        null=True,
        help_text='Link to your Privacy Policy (can be external)'
    )
    cancellation_policy_url = models.URLField(
        blank=True,
        null=True,
        help_text='Link to your Cancellation Policy (can be external)'
    )
    
    # Verification & Status
    is_verified = models.BooleanField(
        default=False,
        help_text='Whether the provider is verified by admin'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether the provider account is active'
    )
    
    # Custom Domain Configuration (PRO plan only)
    custom_domain = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        unique=True,
        help_text='Custom domain or subdomain (e.g., ramesh-salon.yourdomain.com or www.rameshsalon.com)'
    )
    custom_domain_type = models.CharField(
        max_length=20,
        choices=[
            ('none', 'Default'),
            ('subdomain', 'Custom Subdomain'),
            ('domain', 'Custom Domain')
        ],
        default='none',
        help_text='Type of custom domain configuration'
    )
    domain_verified = models.BooleanField(
        default=False,
        help_text='Whether the domain has been verified'
    )
    domain_verification_code = models.CharField(
        max_length=100, 
        blank=True,
        help_text='Random code for domain verification'
    )
    ssl_enabled = models.BooleanField(
        default=False,
        help_text='Whether SSL is enabled for the custom domain'
    )
    domain_added_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='When the domain was added'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Service Provider'
        verbose_name_plural = 'Service Providers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.business_name} ({self.user.email})"
    
    def save(self, *args, **kwargs):
        # Generate unique booking URL if not set
        if not self.unique_booking_url:
            base_slug = slugify(self.business_name)
            unique_slug = base_slug
            counter = 1
            while ServiceProvider.objects.filter(unique_booking_url=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.unique_booking_url = unique_slug
        
        # No trial setup needed
        super().save(*args, **kwargs)
    
    # Plan Management Methods
    def is_pro(self):
        """Check if provider has active PRO plan."""
        if self.current_plan == 'pro':
            # Check if plan hasn't expired
            if self.plan_end_date is None or self.plan_end_date >= timezone.now().date():
                return True
        return False
    
    def has_pro_features(self):
        """Check if provider has PRO features."""
        return self.is_pro()
        
    def get_primary_url(self):
        """
        Returns the primary URL for this provider.
        Only returns custom domain if the provider is on PRO plan and domain is verified.
        """
        if self.custom_domain and self.domain_verified and self.has_pro_features():
            protocol = 'https' if self.ssl_enabled else 'http'
            return f"{protocol}://{self.custom_domain}"
        # For free users or if domain is not verified, use the default URL
        return f"{settings.DEFAULT_SCHEME}://{settings.DEFAULT_DOMAIN}/salon/{self.unique_booking_url}"
    
    # Usage Limit Methods
    def can_create_appointment(self):
        """Check if provider can create a new appointment."""
        if self.has_pro_features():
            return True
        # FREE plan: 5 appointments per month
        return self.appointments_this_month < settings.FREE_PLAN_APPOINTMENT_LIMIT
    
    def remaining_appointments(self):
        """Get remaining appointments for the month."""
        if self.has_pro_features():
            return "Unlimited"
        remaining = settings.FREE_PLAN_APPOINTMENT_LIMIT - self.appointments_this_month
        return max(0, remaining)
    
    def can_add_service(self):
        """Check if provider can add more services."""
        if self.has_pro_features():
            return True
        # FREE plan: maximum 3 services
        return self.services.count() < settings.FREE_PLAN_SERVICE_LIMIT
    
    def increment_appointment_count(self):
        """Increment monthly appointment counter."""
        self.appointments_this_month += 1
        self.save(update_fields=['appointments_this_month'])
    
    def reset_monthly_counter(self):
        """Reset monthly appointment counter (called on 1st of each month)."""
        self.appointments_this_month = 0
        self.last_reset_date = timezone.now().date()
        self.save(update_fields=['appointments_this_month', 'last_reset_date'])
    
    def upgrade_to_pro(self, duration_months=1, is_trial=False):
        """
        Upgrade provider to PRO plan.
        
        Args:
            duration_months (int): Number of months for the subscription
            is_trial (bool): Whether this is a trial upgrade (default: False)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Starting {'trial ' if is_trial else ''}upgrade to PRO for provider: {self.id} - {self.business_name}")
            
            # Update plan details
            self.current_plan = 'pro'
            self.plan_start_date = timezone.now().date()
            self.plan_end_date = timezone.now().date() + timezone.timedelta(days=30 * duration_months)
            
            # Handle trial status
            if is_trial:
                self.is_trial_active = True
                self.trial_end_date = self.plan_end_date
            else:
                self.is_trial_active = False
                self.trial_end_date = None
            
            # Save all fields to ensure changes are persisted
            update_fields = [
                'current_plan',
                'plan_start_date',
                'plan_end_date',
                'is_trial_active',
                'trial_end_date',
                'updated_at'
            ]
            
            self.save(update_fields=update_fields)
            logger.info(f"Successfully upgraded provider {self.id} to PRO plan. Trial: {is_trial}, End date: {self.plan_end_date}")
            
            logger.info(f"Successfully upgraded provider {self.id} to PRO plan. New plan end date: {self.plan_end_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error upgrading provider {self.id} to PRO plan: {str(e)}", exc_info=True)
            return False
    
    def downgrade_to_free(self):
        """Downgrade provider to FREE plan."""
        self.current_plan = 'free'
        # Set plan end date to 30 days from now for free plan
        self.plan_end_date = timezone.now().date() + timezone.timedelta(days=30)
        self.save(update_fields=['current_plan', 'plan_end_date', 'updated_at'])
    
    def get_plan_display_name(self):
        """Get user-friendly plan name."""
        if self.is_on_trial():
            return "PRO (Trial)"
        return dict(self.PLAN_CHOICES).get(self.current_plan, 'Free')
    
    # Staff Management Methods (PRO plan only)
    def can_add_staff(self):
        """Check if provider can add more staff members (PRO plan only)."""
        if not self.is_pro():
            return False
        # PRO plan: Allow up to MAX_STAFF_MEMBERS_PRO staff members
        return self.staff_members.count() < MAX_STAFF_MEMBERS_PRO
    
    def get_staff_count(self):
        """Get number of active staff members."""
        return self.staff_members.filter(is_active=True).count()
    
    def get_active_staff(self):
        """Get all active staff members."""
        return self.staff_members.filter(is_active=True).order_by('display_order', 'name')


class Service(models.Model):
    """
    Services offered by a Service Provider.
    """
    
    DURATION_CHOICES = [
        (15, '15 minutes'),
        (30, '30 minutes'),
        (45, '45 minutes'),
        (60, '1 hour'),
        (90, '1.5 hours'),
        (120, '2 hours'),
        (180, '3 hours'),
    ]
    
    service_provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='services'
    )
    
    service_name = models.CharField(
        max_length=200,
        help_text='Name of the service (e.g., "Haircut", "Yoga Session")'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Detailed description of the service'
    )
    
    duration_minutes = models.IntegerField(
        choices=DURATION_CHOICES,
        default=60,
        help_text='Duration of the service'
    )
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Price in INR'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this service is currently offered'
    )
    
    # NEW: allow service-specific availability
    use_custom_availability = models.BooleanField(
        default=False,
        help_text="If True, this service will use its own custom availability instead of provider defaults"
    )

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['service_name']
        unique_together = ['service_provider', 'service_name']
    
    def __str__(self):
        return f"{self.service_name} - ₹{self.price} ({self.duration_minutes} min)"
    
    def get_duration_display_short(self):
        """Get short duration display."""
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        else:
            return f"{minutes}m"


    # Service-specific availability is supported via `ServiceAvailability` model below.


class ServiceAvailability(models.Model):
    """Custom availability schedule for specific services."""

    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='custom_availability'
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Service Availability'
        verbose_name_plural = 'Service Availabilities'
        constraints = [
            models.UniqueConstraint(fields=['service', 'day_of_week'], name='unique_service_day')
        ]

    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK).get(self.day_of_week, str(self.day_of_week))
        return f"{self.service.service_name} - {day_name} ({self.start_time}-{self.end_time})"


class Testimonial(models.Model):
    """Client testimonials for service providers."""
    
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    service_provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='testimonials'
    )
    client_name = models.CharField(max_length=200)
    client_photo = models.ImageField(
        upload_to=upload_testimonial_photo,
        blank=True,
        null=True
    )
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    testimonial_text = models.TextField(max_length=500)
    date_added = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date_added']
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'
    
    def __str__(self):
        return f"{self.client_name} - {self.service_provider.business_name}"


class HeroImage(models.Model):
    """Hero/banner images for provider profile."""
    
    service_provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='hero_images'
    )
    image = models.ImageField(upload_to=upload_hero_image)
    caption = models.CharField(max_length=200, blank=True, null=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Hero Image'
        verbose_name_plural = 'Hero Images'
    
    def __str__(self):
        return f"Hero - {self.service_provider.business_name} ({self.display_order})"


class TeamMember(models.Model):
    """Team members/practitioners for service provider."""
    
    service_provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='team_members'
    )
    name = models.CharField(max_length=200)
    photo = models.ImageField(
        upload_to=upload_team_photo,
        blank=True,
        null=True
    )
    role_title = models.CharField(
        max_length=200,
        help_text='e.g., Senior Stylist, Yoga Instructor'
    )
    specialties = models.TextField(
        blank=True,
        null=True,
        help_text='e.g., Hair coloring, Keratin treatments'
    )
    bio = models.TextField(
        blank=True,
        null=True,
        max_length=500
    )
    credentials = models.TextField(
        blank=True,
        null=True,
        help_text='e.g., MBA, 10 years experience'
    )
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Team Member'
        verbose_name_plural = 'Team Members'
    
    def __str__(self):
        return f"{self.name} - {self.role_title}"

