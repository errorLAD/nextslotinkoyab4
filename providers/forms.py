"""
Forms for provider management with proper image upload handling.
"""
from django import forms
from .models import (
    ServiceProvider, Service, ServiceAvailability,
    Testimonial, HeroImage, TeamMember
)
from appointments.models import Appointment
from django.forms import inlineformset_factory


class ServiceProviderForm(forms.ModelForm):
    """
    Form for creating/editing service provider profile with image uploads.
    """
    
    class Meta:
        model = ServiceProvider
        fields = [
            'business_name', 'business_type', 'description',
            'phone', 'whatsapp_number',
            'business_address', 'city', 'state', 'pincode',
            'logo', 'profile_image', 'hero_color',
            'mission_statement', 'vision_statement', 'about_us',
            'instagram_url', 'facebook_url', 'twitter_url', 'linkedin_url', 'youtube_url',
            'terms_conditions_url', 'privacy_policy_url', 'cancellation_policy_url'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Business Name'}),
            'business_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description...'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9876543210'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9876543210 (optional)'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '400001'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'hero_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color', 'style': 'width: 80px; height: 40px; padding: 2px;'}),
            'mission_statement': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Your mission...'}),
            'vision_statement': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Your vision...'}),
            'about_us': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'About your business...'}),
            'instagram_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://instagram.com/...'}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://facebook.com/...'}),
            'twitter_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/...'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/...'}),
            'youtube_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/...'}),
            'terms_conditions_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'privacy_policy_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'cancellation_policy_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }


class ServiceForm(forms.ModelForm):
    """Form for creating/editing services."""
    class Meta:
        model = Service
        fields = ['service_name', 'description', 'duration_minutes', 'price', 'use_custom_availability', 'is_active']
        widgets = {
            'service_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Haircut'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'duration_minutes': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '₹'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class ServiceAvailabilityForm(forms.ModelForm):
    class Meta:
        model = ServiceAvailability
        fields = ['day_of_week', 'start_time', 'end_time', 'is_available']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


ServiceAvailabilityFormSet = inlineformset_factory(
    Service, ServiceAvailability, form=ServiceAvailabilityForm,
    extra=7, max_num=7, can_delete=True
)


class AppointmentForm(forms.ModelForm):
    """Form for creating/editing appointments."""
    class Meta:
        model = Appointment
        fields = ['service', 'client_name', 'client_phone', 'client_email', 'appointment_date', 'appointment_time', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }
    
    def __init__(self, *args, **kwargs):
        self.provider = kwargs.pop('provider', None)
        super().__init__(*args, **kwargs)
        if self.provider:
            self.fields['service'].queryset = Service.objects.filter(service_provider=self.provider, is_active=True)


class PublicBookingForm(forms.ModelForm):
    """Form for public booking page."""
    class Meta:
        model = Appointment
        fields = ['service', 'client_name', 'client_phone', 'client_email', 'appointment_date', 'appointment_time', 'notes']
        widgets = {
            'service': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Your Full Name'}),
            'client_phone': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '9876543210'}),
            'client_email': forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'email@example.com'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control form-control-lg', 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any special requests?'})
        }
    
    def __init__(self, *args, **kwargs):
        self.provider = kwargs.pop('provider', None)
        super().__init__(*args, **kwargs)
        if self.provider:
            self.fields['service'].queryset = Service.objects.filter(service_provider=self.provider, is_active=True)


class HeroImageForm(forms.ModelForm):
    """Form for hero images."""
    class Meta:
        model = HeroImage
        fields = ['image', 'caption', 'display_order', 'is_active']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Caption (optional)'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


HeroImageFormSet = inlineformset_factory(
    ServiceProvider, HeroImage, form=HeroImageForm,
    extra=0, max_num=5, can_delete=True
)


class TeamMemberForm(forms.ModelForm):
    """Form for team members with photo."""
    class Meta:
        model = TeamMember
        fields = ['name', 'photo', 'role_title', 'specialties', 'bio', 'credentials', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'role_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Senior Stylist'}),
            'specialties': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Specialties...'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Bio...'}),
            'credentials': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Credentials...'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


TeamMemberFormSet = inlineformset_factory(
    ServiceProvider, TeamMember, form=TeamMemberForm,
    extra=0, can_delete=True
)


class TestimonialForm(forms.ModelForm):
    """Form for testimonials with client photo."""
    class Meta:
        model = Testimonial
        fields = ['client_name', 'client_photo', 'rating', 'testimonial_text', 'is_featured', 'is_active']
        widgets = {
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client name'}),
            'client_photo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'testimonial_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Testimonial...'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


TestimonialFormSet = inlineformset_factory(
    ServiceProvider, Testimonial, form=TestimonialForm,
    extra=0, can_delete=True
)

