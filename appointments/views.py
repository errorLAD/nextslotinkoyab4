"""
Views for public booking and client appointments.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from providers.models import ServiceProvider
from .models import Appointment
import json


def public_booking_page(request, slug=None):
    """
    Public booking page for a service provider.
    Shows login/signup modal for unauthenticated users.
    
    If accessed via custom domain, the provider is set in request.custom_domain_provider
    """
    # Check if this is a custom domain request
    if hasattr(request, 'custom_domain_provider') and request.custom_domain_provider:
        provider = request.custom_domain_provider
    elif slug:
        provider = get_object_or_404(ServiceProvider, unique_booking_url=slug, is_active=True)
    else:
        # No slug and no custom domain - redirect to providers list
        return redirect('appointments:book_providers')
    services = provider.services.filter(is_active=True)

    # Collect availability from all services' custom availability
    # Create a dict to consolidate availability by day (dedupe by day_of_week)
    availability_by_day = {}

    for service in services:
        service_availability = service.custom_availability.filter(is_available=True).order_by('day_of_week')
        for slot in service_availability:
            day_key = slot.day_of_week
            # Keep the first seen slot for that day (you may want to merge ranges later)
            if day_key not in availability_by_day:
                availability_by_day[day_key] = {
                    'day_of_week': day_key,
                    'day_name': slot.get_day_of_week_display(),
                    'start_time': slot.start_time,
                    'end_time': slot.end_time,
                    'is_available': slot.is_available,
                }

    # Convert consolidated dict to a sorted list for template consumption
    availability = sorted(
        availability_by_day.values(),
        key=lambda x: x['day_of_week']
    )
    
    # Build services JSON for JavaScript
    services_json = []
    for service in services:
        services_json.append({
            'id': service.id,
            'name': service.service_name,
            'price': float(service.price),
            'duration': service.duration_minutes,
            'description': service.description[:100] if service.description else ''
        })
    
    # Prepare availability as JSON (list of dicts with day info)
    availability_json = []
    for slot in availability:
        availability_json.append({
            'day_of_week': slot['day_of_week'],
            'day_name': slot['day_name'],
            'start_time': str(slot['start_time']),
            'end_time': str(slot['end_time']),
            'is_available': slot['is_available']
        })
    
    # Initialize context with provider data
    context = {
        'provider': provider,
        'services': services,
        'services_json': json.dumps(services_json),
        'availability': availability_json,
        'hero_images': provider.hero_images.filter(is_active=True).order_by('display_order'),
        'testimonials': provider.testimonials.filter(is_active=True).order_by('-is_featured', '-date_added')[:6],
        'team_members': provider.team_members.filter(is_active=True).order_by('display_order'),
        'client_name': '',
        'client_email': '',
        'show_auth_modal': False
    }
    
    # If user is authenticated, pre-fill their information
    if request.user.is_authenticated:
        client_name = f"{request.user.first_name} {request.user.last_name}".strip()
        if not client_name:
            client_name = request.user.email.split('@')[0]  # Use email prefix as fallback
            
        context.update({
            'client_name': client_name,
            'client_email': request.user.email,
        })
    else:
        # Show auth modal for unauthenticated users
        context['show_auth_modal'] = True
        
        # If coming from a redirect with next parameter, show appropriate message
        if 'next' in request.GET:
            messages.info(request, 'Please sign in or create an account to continue with your booking.')
    
    # Render the new beautiful booking page
    return render(request, 'appointments/booking.html', context)


def confirm_booking(request, slug):
    """
    Confirm and create a booking from public page.
    Requires user to be logged in.
    """
    # Redirect to login if user is not authenticated
    if not request.user.is_authenticated:
        messages.warning(request, 'You need to be logged in to book a service.')
        return redirect(f'/accounts/login/?next={request.path}')
        
    provider = get_object_or_404(ServiceProvider, unique_booking_url=slug, is_active=True)
    
    if request.method == 'POST':
        service_id = request.POST.get('service')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        client_phone = request.POST.get('client_phone')
        notes = request.POST.get('notes', '')
        
        # Get user information from the authenticated user
        client_name = f"{request.user.first_name} {request.user.last_name}".strip()
        if not client_name:
            client_name = request.user.email.split('@')[0]  # Use email prefix as fallback
            
        client_email = request.user.email
        
        # Create appointment
        appointment = Appointment.objects.create(
            service_provider=provider,
            service_id=service_id,
            client=request.user,  # Always set the authenticated user
            client_name=client_name,
            client_phone=client_phone,
            client_email=client_email,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status='pending',
            notes=notes
        )
        
        return redirect('appointments:booking_success', pk=appointment.pk)
    
    return redirect('appointments:public_booking', slug=slug)


def booking_success(request, pk):
    """
    Booking confirmation success page.
    This view is accessible to both authenticated and unauthenticated users
    as long as they have the correct booking ID.
    """
    # Skip provider_required decorator for this view
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # If user is a provider and owns this appointment, redirect to provider's dashboard
    if hasattr(request.user, 'is_provider') and request.user.is_provider:
        return redirect('providers:dashboard')
    
    # For clients or unauthenticated users, show the booking success page
    context = {
        'appointment': appointment,
        'is_authenticated': request.user.is_authenticated,
    }
    
    # Use a different template for unauthenticated users if needed
    return render(request, 'appointments/booking_success.html', context)


@login_required
def my_appointments(request):
    """
    Client's appointment list with separate tabs for upcoming and past appointments.
    """
    if request.user.is_provider:
        return redirect('providers:dashboard')
    
    from django.utils import timezone
    
    # Get upcoming appointments (today and future)
    upcoming_appointments = Appointment.objects.filter(
        client=request.user,
        appointment_date__gte=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).order_by('appointment_date', 'appointment_time')
    
    # Get past appointments
    past_appointments = Appointment.objects.filter(
        client=request.user,
        appointment_date__lt=timezone.now().date()
    ).exclude(status__in=['pending', 'confirmed']).order_by('-appointment_date', '-appointment_time')
    
    # Get cancelled appointments
    cancelled_appointments = Appointment.objects.filter(
        client=request.user,
        status='cancelled'
    ).order_by('-updated_at')
    
    context = {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'cancelled_appointments': cancelled_appointments,
    }
    
    return render(request, 'appointments/my_appointments.html', context)


def home_redirect(request):
    """
    Home page - redirect to first available provider's booking page.
    """
    # Get first active provider
    provider = ServiceProvider.objects.filter(is_active=True).first()
    
    if provider:
        return redirect('appointments:public_booking', slug=provider.unique_booking_url)
    else:
        # If no providers, go to browse page
        return redirect('appointments:browse_providers')


def browse_providers(request):
    """
    Browse available service providers.
    """
    # Show all active providers (verification is optional)
    providers = ServiceProvider.objects.filter(
        is_active=True
    ).order_by('-created_at')
    
    # Filter by business type
    business_type = request.GET.get('type')
    if business_type:
        providers = providers.filter(business_type=business_type)
    
    # Filter by city
    city = request.GET.get('city')
    if city:
        providers = providers.filter(city__icontains=city)
    
    context = {
        'providers': providers,
        'business_types': ServiceProvider.BUSINESS_TYPE_CHOICES,
    }
    
    return render(request, 'appointments/browse_providers.html', context)


def book_providers(request):
    """
    Book page - shows available service providers for booking.
    This is the main booking page for clients after signup.
    Only shows PRO plan providers in the store.
    """
    from django.utils import timezone
    
    # Show only active PRO plan providers
    providers = ServiceProvider.objects.filter(
        is_active=True,
        current_plan='pro'
    ).exclude(
        # Exclude expired PRO plans
        plan_end_date__lt=timezone.now().date()
    ).order_by('-created_at')
    
    # Filter by business type
    business_type = request.GET.get('type')
    if business_type:
        providers = providers.filter(business_type=business_type)
    
    # Filter by city
    city = request.GET.get('city')
    if city:
        providers = providers.filter(city__icontains=city)
    
    # Search by name
    search = request.GET.get('search')
    if search:
        providers = providers.filter(business_name__icontains=search)
    
    context = {
        'providers': providers,
        'business_types': ServiceProvider.BUSINESS_TYPE_CHOICES,
    }
    
    return render(request, 'appointments/book_providers.html', context)
