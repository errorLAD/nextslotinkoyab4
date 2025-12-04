"""
Views for managing custom domains for service providers.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from .models import ServiceProvider
from .domain_utils import setup_custom_domain, verify_domain_ownership, generate_verification_code

@login_required
def custom_domain_page(request):
    """
    Dedicated page for managing custom domain settings.
    """
    if not hasattr(request.user, 'is_provider') or not request.user.is_provider:
        raise PermissionDenied("You don't have permission to access this page.")
    
    provider = request.user.provider_profile
    is_pro = provider.has_pro_features()
    
    if not is_pro:
        messages.info(request, 'Custom domains are only available for PRO users. Upgrade to PRO to use this feature.')
    
    context = {
        'provider': provider,
        'default_domain': settings.DEFAULT_DOMAIN,
        'is_pro': is_pro,
    }
    
    return render(request, 'providers/custom_domain.html', context)

@login_required
def domain_settings(request):
    """
    View for managing domain settings.
    Only available for PRO users.
    """
    # Only service providers can access this page
    if not hasattr(request.user, 'is_provider') or not request.user.is_provider:
        raise PermissionDenied("You don't have permission to access this page.")
    
    provider = request.user.provider_profile
    is_pro = provider.has_pro_features()
    
    # If not PRO, show the page but with limited functionality
    if not is_pro:
        messages.info(request, 'Custom domains are only available for PRO users. Upgrade to PRO to use this feature.')
    
    context = {
        'provider': provider,
        'default_domain': settings.DEFAULT_DOMAIN,
        'is_pro': is_pro,
    }
    
    return render(request, 'providers/domain/settings.html', context)

@login_required
@require_http_methods(['POST'])
def add_custom_domain(request):
    """
    Handle adding a custom domain or subdomain.
    Only available for PRO users.
    """
    if not hasattr(request.user, 'is_provider') or not request.user.is_provider:
        raise PermissionDenied("You don't have permission to perform this action.")
    
    provider = request.user.provider_profile
    
    # Check if user has PRO features
    if not provider.has_pro_features():
        messages.warning(request, 'Custom domains are only available on the PRO plan. Please upgrade to continue.')
        return redirect('subscriptions:upgrade_to_pro')
    
    # Support both 'domain' and 'custom_domain' parameter names
    domain = request.POST.get('domain', '').strip().lower()
    if not domain:
        domain = request.POST.get('custom_domain', '').strip().lower()
    
    domain_type = request.POST.get('domain_type', 'domain')
    
    # Validate domain type
    if domain_type not in ['subdomain', 'domain']:
        domain_type = 'domain'
    
    # Clean up domain - remove protocol if present
    domain = domain.replace('https://', '').replace('http://', '').strip('/')
    
    # For subdomains, validate and construct full domain
    if domain_type == 'subdomain':
        # Basic validation
        if not domain.replace('-', '').isalnum():
            messages.error(request, 'Subdomain can only contain letters, numbers, and hyphens.')
            return redirect('providers:dashboard')
        
        if len(domain) < 3 or len(domain) > 63:
            messages.error(request, 'Subdomain must be between 3 and 63 characters long.')
            return redirect('providers:dashboard')
        
        # Construct full domain
        domain = f"{domain}.{settings.DEFAULT_DOMAIN}"
    else:
        # For custom domains, validate the domain format
        if not is_valid_domain(domain):
            messages.error(request, 'Please enter a valid domain name (e.g., book.yourdomain.com).')
            return redirect('providers:dashboard')
    
    # Setup the domain
    success, message, verification_code = setup_custom_domain(provider, domain, domain_type)
    
    if success:
        messages.success(request, f'Domain "{domain}" added! Please configure DNS records in Cloudflare to complete setup.')
        return redirect('providers:custom_domain')
    else:
        messages.error(request, message)
        return redirect('providers:custom_domain')

def is_valid_domain(domain):
    """
    Basic domain validation.
    """
    if not domain or len(domain) > 255:
        return False
    
    # Check for at least one dot and no spaces
    if '.' not in domain or ' ' in domain:
        return False
    
    # Check each part of the domain
    parts = domain.split('.')
    for part in parts:
        if not part or len(part) > 63:
            return False
        if not all(c.isalnum() or c == '-' for c in part):
            return False
        if part.startswith('-') or part.endswith('-'):
            return False
    
    return True

@login_required
def domain_verification(request):
    """
    Show domain verification instructions and status.
    """
    if not hasattr(request.user, 'is_provider') or not request.user.is_provider:
        raise PermissionDenied("You don't have permission to access this page.")
    
    provider = request.user.provider_profile
    
    if not provider.custom_domain:
        messages.warning(request, 'No custom domain configured.')
        return redirect('providers:domain_settings')
    
    context = {
        'provider': provider,
        'default_domain': settings.DEFAULT_DOMAIN,
        'verification_code': provider.domain_verification_code,
    }
    
    return render(request, 'providers/domain/verification.html', context)

@login_required
def verify_domain(request):
    """
    Verify domain ownership by checking DNS records.
    """
    if not hasattr(request.user, 'is_provider') or not request.user.is_provider:
        raise PermissionDenied("You don't have permission to perform this action.")
    
    provider = request.user.provider_profile
    
    if not provider.has_pro_features():
        messages.warning(request, 'Custom domains are only available on the PRO plan. Please upgrade to continue.')
        return redirect('subscriptions:upgrade_to_pro')
    
    if not provider.custom_domain or not provider.domain_verification_code:
        messages.error(request, 'No domain or verification code found.')
        return redirect('providers:dashboard')
    
    success, message = verify_domain_ownership(provider)
    
    if success:
        messages.success(request, 'Domain verified successfully! Your custom domain is now active with SSL.')
    else:
        messages.warning(request, message + ' Make sure DNS records are configured in Cloudflare and propagated (may take up to 24 hours).')
    
    return redirect('providers:custom_domain')

@login_required
@require_http_methods(['POST'])
def remove_domain(request):
    """
    Remove a custom domain from the provider's account.
    """
    if not hasattr(request.user, 'is_provider') or not request.user.is_provider:
        raise PermissionDenied("You don't have permission to perform this action.")
    
    provider = request.user.provider_profile
    
    domain = provider.custom_domain
    
    # Clear the custom domain and verification status
    provider.custom_domain = None
    provider.custom_domain_type = 'none'  # Reset to default, not None
    provider.domain_verified = False
    provider.domain_verification_code = ''
    provider.ssl_enabled = False
    provider.save()
    
    messages.success(request, f'Domain "{domain}" has been removed successfully.')
    return redirect('providers:custom_domain')
