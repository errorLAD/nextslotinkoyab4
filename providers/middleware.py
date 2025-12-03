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
            
        host = request.get_host().split(':')[0]
        
        # Skip if it's the default domain
        if host != settings.DEFAULT_DOMAIN and not any(host.endswith(f'.{domain}') for domain in settings.ALLOWED_HOSTS):
            try:
                # Try to find a provider with this custom domain
                provider = ServiceProvider.objects.get(
                    custom_domain=host,
                    domain_verified=True,
                    is_active=True
                )
                
                # Set provider in request for views to use
                request.custom_domain_provider = provider
                
                # Set a flag to indicate this is a custom domain request
                request.is_custom_domain = True
                
                # If SSL is enabled, ensure we're using HTTPS
                if provider.ssl_enabled and not request.is_secure():
                    from django.urls import reverse
                    from django.shortcuts import redirect
                    return redirect(f'https://{host}{request.get_full_path()}')
                    
            except ServiceProvider.DoesNotExist:
                # Check if this is a subdomain request (e.g., ramesh-salon.yourdomain.com)
                if f'.{settings.DEFAULT_DOMAIN}' in host:
                    subdomain = host.replace(f'.{settings.DEFAULT_DOMAIN}', '')
                    try:
                        provider = ServiceProvider.objects.get(
                            custom_domain=f"{subdomain}.{settings.DEFAULT_DOMAIN}",
                            custom_domain_type='subdomain',
                            domain_verified=True,
                            is_active=True
                        )
                        request.custom_domain_provider = provider
                        request.is_custom_domain = True
                        
                        # If SSL is enabled, ensure we're using HTTPS
                        if provider.ssl_enabled and not request.is_secure():
                            from django.urls import reverse
                            from django.shortcuts import redirect
                            return redirect(f'https://{host}{request.get_full_path()}')
                            
                    except ServiceProvider.DoesNotExist:
                        pass
        
        response = self.get_response(request)
        return response
