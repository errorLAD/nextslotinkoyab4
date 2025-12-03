"""
Views for service provider dashboard and management.
"""
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import ServiceProvider, Service
from .decorators import provider_required, check_service_limit, check_appointment_limit
from appointments.models import Appointment
from .forms import (
    ServiceProviderForm, ServiceForm, AppointmentForm,
    TestimonialFormSet, TeamMemberFormSet
)
from django.db.models import Q


@login_required
@provider_required
def dashboard(request):
    """
    Provider dashboard with overview.
    """
    provider = request.user.provider_profile
    
    # Get today's appointments
    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(
        service_provider=provider,
        appointment_date=today
    ).order_by('appointment_time')
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        service_provider=provider,
        appointment_date__gt=today,
        status__in=['pending', 'confirmed']
    ).order_by('appointment_date', 'appointment_time')[:5]
    
    # Statistics
    total_appointments = Appointment.objects.filter(service_provider=provider).count()
    pending_appointments = Appointment.objects.filter(
        service_provider=provider,
        status='pending'
    ).count()
    
    context = {
        'provider': provider,
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'services_count': provider.services.filter(is_active=True).count(),
    }
    
    return render(request, 'providers/dashboard.html', context)


@login_required
def setup_profile(request):
    """
    Initial provider profile setup.
    """
    # Check if profile already exists
    if hasattr(request.user, 'provider_profile'):
        return redirect('providers:edit_profile')
    
    if request.method == 'POST':
        business_name = request.POST.get('business_name')
        business_type = request.POST.get('business_type')
        phone = request.POST.get('phone')
        city = request.POST.get('city')
        
        # Create provider profile
        provider = ServiceProvider.objects.create(
            user=request.user,
            business_name=business_name,
            business_type=business_type,
            phone=phone,
            city=city
        )
        
        messages.success(request, 'Profile created successfully! Start adding your services.')
        return redirect('providers:dashboard')
    
    return render(request, 'providers/setup_profile.html')


@login_required
@provider_required
def edit_profile(request):
    """
    Provider profile editor with support for testimonials, team members, hero images and social/legal links.
    """
    from .forms import HeroImageFormSet
    
    provider = request.user.provider_profile
    
    if request.method == 'POST':
        # Include request.FILES for image uploads
        form = ServiceProviderForm(request.POST, request.FILES, instance=provider)
        testimonial_formset = TestimonialFormSet(request.POST, request.FILES, instance=provider, prefix='testimonials')
        team_member_formset = TeamMemberFormSet(request.POST, request.FILES, instance=provider, prefix='team_members')
        hero_image_formset = HeroImageFormSet(request.POST, request.FILES, instance=provider, prefix='hero_images')
        
        # Validate all formsets
        form_valid = form.is_valid()
        testimonial_valid = testimonial_formset.is_valid()
        team_valid = team_member_formset.is_valid()
        hero_valid = hero_image_formset.is_valid()
        
        if form_valid and testimonial_valid and team_valid and hero_valid:
            # Save all forms
            try:
                with transaction.atomic():
                    form.save()
                    testimonial_formset.save()
                    team_member_formset.save()
                    hero_image_formset.save()
                
                messages.success(request, 'Profile updated successfully!')
                return redirect('providers:edit_profile')
            except Exception as e:
                messages.error(request, f'Error saving profile: {str(e)}')
        else:
            # Show form errors
            if not form_valid:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
            if not testimonial_valid:
                messages.error(request, 'Please fix errors in testimonials section.')
                for i, form_errors in enumerate(testimonial_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Testimonial {i+1} - {field}: {error}')
            if not team_valid:
                messages.error(request, 'Please fix errors in team members section.')
                for i, form_errors in enumerate(team_member_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Team Member {i+1} - {field}: {error}')
            if not hero_valid:
                messages.error(request, 'Please fix errors in hero images section.')
                for i, form_errors in enumerate(hero_image_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Hero Image {i+1} - {field}: {error}')
    else:
        form = ServiceProviderForm(instance=provider)
        testimonial_formset = TestimonialFormSet(instance=provider, prefix='testimonials')
        team_member_formset = TeamMemberFormSet(instance=provider, prefix='team_members')
        hero_image_formset = HeroImageFormSet(instance=provider, prefix='hero_images')
    
    context = {
        'form': form,
        'testimonial_formset': testimonial_formset,
        'team_member_formset': team_member_formset,
        'hero_image_formset': hero_image_formset,
        'provider': provider,
    }
    
    return render(request, 'providers/edit_profile.html', context)


@login_required
@provider_required
def service_list(request):
    """
    List all services for the provider.
    """
    provider = request.user.provider_profile
    services = provider.services.all().order_by('-is_active', 'service_name')
    
    context = {
        'provider': provider,
        'services': services,
        'can_add_more': provider.can_add_service(),
    }
    
    return render(request, 'providers/service_list.html', context)


@login_required
@provider_required
@check_service_limit
def add_service(request):
    """
    Add a new service with optional custom availability.
    """
    
    provider = request.user.provider_profile
    
    if request.method == 'POST':
        service_form = ServiceForm(request.POST, request=request)
        
        if service_form.is_valid():
            service = service_form.save(commit=False)
            service.service_provider = provider
            service.save()
            messages.success(request, 'Service added successfully!')
            return redirect('providers:service_list')
        else:
            availability_formset = None
    else:
        service_form = ServiceForm(request=request)
        availability_formset = None
    
    context = {
        'provider': provider,
        'service_form': service_form,
        'availability_formset': availability_formset,
    }
    
    return render(request, 'providers/add_service.html', context)


@login_required
@provider_required
def edit_service(request, pk):
    """
    Edit an existing service and its availability.
    """
    
    provider = request.user.provider_profile
    service = get_object_or_404(Service, pk=pk, service_provider=provider)
    
    if request.method == 'POST':
        service_form = ServiceForm(request.POST, request=request, instance=service)
        
        if service_form.is_valid():
            service = service_form.save()
            messages.success(request, 'Service updated!')
            return redirect('providers:service_list')
        else:
            availability_formset = None
    else:
        service_form = ServiceForm(request=request, instance=service)
        availability_formset = None
    
    context = {
        'provider': provider,
        'service': service,
        'service_form': service_form,
        'availability_formset': availability_formset,
    }
    
    return render(request, 'providers/edit_service.html', context)


@login_required
@provider_required
def delete_service(request, pk):
    """
    Delete a service.
    """
    provider = request.user.provider_profile
    service = get_object_or_404(Service, pk=pk, service_provider=provider)
    
    if request.method == 'POST':
        service_name = service.service_name
        service.delete()
        messages.success(request, f'Service "{service_name}" deleted successfully!')
        return redirect('providers:service_list')
    
    context = {
        'provider': provider,
        'service': service,
    }
    
    return render(request, 'providers/delete_service.html', context)


@login_required
@provider_required
def appointment_list(request):
    """
    List all appointments for the provider.
    """
    provider = request.user.provider_profile
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    
    appointments = Appointment.objects.filter(service_provider=provider)
    
    if status_filter != 'all':
        appointments = appointments.filter(status=status_filter)
    
    appointments = appointments.order_by('-appointment_date', '-appointment_time')
    
    context = {
        'provider': provider,
        'appointments': appointments,
        'status_filter': status_filter,
    }
    
    return render(request, 'providers/appointment_list.html', context)


@login_required
@provider_required
@check_appointment_limit
def create_appointment(request):
    """
    Create a walk-in appointment.
    """
    provider = request.user.provider_profile
    services = provider.services.filter(is_active=True)
    
    if request.method == 'POST':
        appointment = Appointment.objects.create(
            service_provider=provider,
            service_id=request.POST.get('service'),
            client_name=request.POST.get('client_name'),
            client_phone=request.POST.get('client_phone'),
            client_email=request.POST.get('client_email', ''),
            appointment_date=request.POST.get('appointment_date'),
            appointment_time=request.POST.get('appointment_time'),
            status='confirmed',
            notes=request.POST.get('notes', '')
        )
        
        messages.success(request, 'Appointment created successfully!')
        return redirect('providers:appointment_detail', pk=appointment.pk)
    
    context = {
        'provider': provider,
        'services': services,
    }
    
    return render(request, 'providers/create_appointment.html', context)


@login_required
@provider_required
def appointment_detail(request, pk):
    """
    View appointment details.
    """
    provider = request.user.provider_profile
    appointment = get_object_or_404(Appointment, pk=pk, service_provider=provider)
    
    context = {
        'provider': provider,
        'appointment': appointment,
    }
    
    return render(request, 'providers/appointment_detail.html', context)


@login_required
@provider_required
def confirm_appointment(request, pk):
    """
    Confirm a pending appointment.
    """
    provider = request.user.provider_profile
    appointment = get_object_or_404(Appointment, pk=pk, service_provider=provider)
    
    if appointment.confirm():
        messages.success(request, 'Appointment confirmed!')
    else:
        messages.error(request, 'Cannot confirm this appointment.')
    
    return redirect('providers:appointment_detail', pk=pk)


@login_required
@provider_required
def cancel_appointment(request, pk):
    """
    Cancel an appointment.
    """
    provider = request.user.provider_profile
    appointment = get_object_or_404(Appointment, pk=pk, service_provider=provider)
    
    if appointment.cancel():
        messages.success(request, 'Appointment cancelled.')
    else:
        messages.error(request, 'Cannot cancel this appointment.')
    
    return redirect('providers:appointment_detail', pk=pk)


@login_required
@provider_required
def complete_appointment(request, pk):
    """
    Mark appointment as completed.
    """
    appointment = get_object_or_404(Appointment, pk=pk, service_provider=request.user.provider_profile)
    
    if request.method == 'POST':
        appointment.status = 'completed'
        appointment.save()
        messages.success(request, 'Appointment marked as completed.')
        return redirect('providers:appointment_list')
    
    return redirect('providers:appointment_detail', pk=appointment.pk)


@login_required
@provider_required
def manage_availability(request):
    # Availability editor removed per user request; return 404 or redirect to dashboard
    messages.info(request, 'Availability management has been removed.')
    return redirect('providers:dashboard')
