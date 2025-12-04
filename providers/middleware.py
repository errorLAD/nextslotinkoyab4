"""
Middleware for subscription plan checking and trial management.
"""
import uuid
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.http import Http404
from django.middleware.csrf import CsrfViewMiddleware
from .models import ServiceProvider


class DynamicCsrfMiddleware(CsrfViewMiddleware):
    """
    Custom CSRF middleware that dynamically allows verified custom domains.
    This checks if the request origin is from a verified provider's custom domain.
    """
    
    def _origin_verified(self, request):
        """
        Override to dynamically check custom domains from database.
        """
        # First, try the default verification
        if super()._origin_verified(request):
            return True
        
        # Get the origin from the request
        request_origin = request.META.get('HTTP_ORIGIN')
        if not request_origin:
            return False
        
        # Extract domain from origin (remove protocol)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(request_origin)
            origin_domain = parsed.netloc.lower()
            
            # Remove port if present
            if ':' in origin_domain:
                origin_domain = origin_domain.split(':')[0]
            
            # Remove www. prefix for comparison
            bare_domain = origin_domain[4:] if origin_domain.startswith('www.') else origin_domain
            
            # Check if this is a verified custom domain
            exists = ServiceProvider.objects.filter(
                domain_verified=True,
                is_active=True
            ).filter(
                # Match exact domain or without www
                custom_domain__iexact=origin_domain
            ).exists()
            
            if exists:
                return True
            
            # Also check bare domain (without www)
            if origin_domain.startswith('www.'):
                exists = ServiceProvider.objects.filter(
                    domain_verified=True,
                    is_active=True,
                    custom_domain__iexact=bare_domain
                ).exists()
                if exists:
                    return True
            
        except Exception:
            pass
        
        return False


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
        
        # Skip if already on a salon booking page (prevent redirect loops)
        if request.path.startswith('/salon/'):
            # Still need to set the provider for context
            host = request.get_host().split(':')[0].lower().strip()
            request.is_custom_domain = False
            request.custom_domain_provider = None
            
            # Try to find provider for this custom domain
            provider = self._find_provider_for_host(host)
            if provider:
                request.is_custom_domain = True
                request.custom_domain_provider = provider
            
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
        provider = self._find_provider_for_host(host)
        
        if provider:
            # Set provider in request for views to use
            request.custom_domain_provider = provider
            request.is_custom_domain = True
            
            # Only redirect root path to booking page
            if request.path == '/' or request.path == '':
                from django.shortcuts import redirect
                return redirect(f'/salon/{provider.unique_booking_url}/')
        
        response = self.get_response(request)
        return response
    
    def _find_provider_for_host(self, host):
        """
        Find a provider matching the given host.
        Checks for exact match, www variant, and subdomain patterns.
        """
        # Remove www. prefix for matching
        bare_host = host[4:] if host.startswith('www.') else host
        www_host = f'www.{bare_host}' if not host.startswith('www.') else host
        
        # Try exact match first
        try:
            return ServiceProvider.objects.get(
                custom_domain__iexact=host,
                domain_verified=True,
                is_active=True
            )
        except ServiceProvider.DoesNotExist:
            pass
        
        # Try without www
        try:
            return ServiceProvider.objects.get(
                custom_domain__iexact=bare_host,
                domain_verified=True,
                is_active=True
            )
        except ServiceProvider.DoesNotExist:
            pass
        
        # Try with www
        try:
            return ServiceProvider.objects.get(
                custom_domain__iexact=www_host,
                domain_verified=True,
                is_active=True
            )
        except ServiceProvider.DoesNotExist:
            pass
        
        # Check subdomain pattern
        default_domain = getattr(settings, 'DEFAULT_DOMAIN', '').lower()
        if default_domain and host.endswith(f'.{default_domain}'):
            try:
                return ServiceProvider.objects.get(
                    custom_domain__iexact=host,
                    custom_domain_type='subdomain',
                    domain_verified=True,
                    is_active=True
                )
            except ServiceProvider.DoesNotExist:
                pass
        
        return None
