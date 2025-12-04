"""
Middleware for subscription plan checking and trial management.
"""
import uuid
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from .models import ServiceProvider


class SubscriptionCheckMiddleware:
    """
    Middleware to check subscription status on each request.
    Handles plan downgrades when PRO subscription expires.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check subscription status for authenticated providers
        if request.user.is_authenticated and hasattr(request.user, 'is_provider'):
            if request.user.is_provider and hasattr(request.user, 'provider_profile'):
                provider = request.user.provider_profile
                today = timezone.now().date()
                
                # Check if PRO subscription has expired
                if provider.current_plan == 'pro' and provider.plan_end_date:
                    if provider.plan_end_date < today:
                        provider.downgrade_to_free()
                        
                        # Show message only once per session
                        if not request.session.get('pro_expiry_shown'):
                            messages.warning(
                                request,
                                'Your PRO subscription has expired. You have been downgraded to the FREE plan.'
                            )
                            request.session['pro_expiry_shown'] = True
        
        response = self.get_response(request)
        return response


class CustomDomainMiddleware:
    """
    Middleware to handle custom domain routing for service providers.
    
    This middleware checks if the request is coming from a custom domain or subdomain
    and routes directly to the provider's booking page.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip for static/media files and admin
        if request.path.startswith(('/static/', '/media/', '/admin/')):
            return self.get_response(request)
        
        # Initialize custom domain flags
        request.custom_domain_provider = None
        request.is_custom_domain = False
            
        host = request.get_host().split(':')[0].lower()
        
        # Get default domain
        default_domain = getattr(settings, 'DEFAULT_DOMAIN', 'localhost')
        
        # Skip if it's localhost or the main app domain
        main_hosts = ['localhost', '127.0.0.1', default_domain]
        # Also skip for Railway app domains
        if any(host == h or host.endswith('.railway.app') or host.endswith('.koyeb.app') for h in main_hosts):
            return self.get_response(request)
        
        # Try to find a provider with this custom domain
        provider = None
        
        # Check for exact custom domain match
        try:
            provider = ServiceProvider.objects.get(
                custom_domain=host,
                domain_verified=True,
                is_active=True
            )
        except ServiceProvider.DoesNotExist:
            # Check if this is a subdomain request
            if f'.{default_domain}' in host:
                subdomain = host.replace(f'.{default_domain}', '')
                try:
                    provider = ServiceProvider.objects.get(
                        custom_domain=f"{subdomain}.{default_domain}",
                        custom_domain_type='subdomain',
                        domain_verified=True,
                        is_active=True
                    )
                except ServiceProvider.DoesNotExist:
                    pass
        
        if provider:
            # Set provider in request for views to use
            request.custom_domain_provider = provider
            request.is_custom_domain = True
            
            # If SSL is enabled, ensure we're using HTTPS
            if provider.ssl_enabled and not request.is_secure():
                return redirect(f'https://{host}{request.get_full_path()}')
            
            # If accessing root path, redirect to provider's booking page
            if request.path == '/' or request.path == '':
                return redirect(f'/appointments/book/{provider.unique_booking_url}/')
        
        response = self.get_response(request)
        return response
