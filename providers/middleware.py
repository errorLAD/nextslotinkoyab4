"""
Middleware for subscription plan checking and trial management.
"""
import uuid
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.http import Http404
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
    and sets the appropriate provider in the request object.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip for static/media files and admin
        if request.path.startswith(('/static/', '/media/', '/admin/')):
            return self.get_response(request)
        
        # Initialize custom domain flags
        request.is_custom_domain = False
        request.custom_domain_provider = None
            
        host = request.get_host().split(':')[0].lower().strip()
        
        # Get hosting domain to skip
        hosting_domain = getattr(settings, 'HOSTING_DOMAIN', '').lower()
        default_domain = getattr(settings, 'DEFAULT_DOMAIN', '').lower()
        
        # Skip if it's the hosting domain (Koyeb, Railway, etc.)
        if host == hosting_domain or host.endswith(f'.{hosting_domain}'):
            return self.get_response(request)
        
        # Skip if it's the default/main domain
        if host == default_domain or host == f'www.{default_domain}':
            return self.get_response(request)
        
        # Skip localhost
        if host in ['localhost', '127.0.0.1']:
            return self.get_response(request)
        
        # Try to find a provider with this custom domain
        try:
            provider = ServiceProvider.objects.get(
                custom_domain__iexact=host,
                domain_verified=True,
                is_active=True
            )
            
            # Set provider in request for views to use
            request.custom_domain_provider = provider
            request.is_custom_domain = True
            
            # Redirect to booking page for this provider
            # If accessing root of custom domain, redirect to the salon booking page
            if request.path == '/' or request.path == '':
                from django.shortcuts import redirect
                return redirect(f'/salon/{provider.unique_booking_url}/')
            
            # If SSL is enabled, ensure we're using HTTPS
            if provider.ssl_enabled and not request.is_secure():
                from django.shortcuts import redirect
                return redirect(f'https://{host}{request.get_full_path()}')
                
        except ServiceProvider.DoesNotExist:
            # Check for www variant
            if host.startswith('www.'):
                bare_host = host[4:]  # Remove www.
                try:
                    provider = ServiceProvider.objects.get(
                        custom_domain__iexact=bare_host,
                        domain_verified=True,
                        is_active=True
                    )
                    request.custom_domain_provider = provider
                    request.is_custom_domain = True
                    
                    if request.path == '/' or request.path == '':
                        from django.shortcuts import redirect
                        return redirect(f'/salon/{provider.unique_booking_url}/')
                        
                except ServiceProvider.DoesNotExist:
                    pass
            
            # Check if this is a subdomain of DEFAULT_DOMAIN
            if default_domain and host.endswith(f'.{default_domain}'):
                subdomain = host.replace(f'.{default_domain}', '')
                try:
                    provider = ServiceProvider.objects.get(
                        custom_domain__iexact=host,
                        custom_domain_type='subdomain',
                        domain_verified=True,
                        is_active=True
                    )
                    request.custom_domain_provider = provider
                    request.is_custom_domain = True
                    
                    if request.path == '/' or request.path == '':
                        from django.shortcuts import redirect
                        return redirect(f'/salon/{provider.unique_booking_url}/')
                    
                except ServiceProvider.DoesNotExist:
                    pass
        
        response = self.get_response(request)
        return response
