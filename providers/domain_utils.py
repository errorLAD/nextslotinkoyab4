"""
Utilities for domain verification and management.
Supports Cloudflare for SSL and DNS management.
Each provider gets unique DNS records for their custom domain.
"""
import dns.resolver
import random
import string
import hashlib
import requests
from django.conf import settings
from django.utils import timezone
from .models import ServiceProvider

def generate_verification_code(length=32):
    """Generate a random verification code for domain verification."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_provider_unique_id(provider_id):
    """
    Generate a unique identifier for provider-specific DNS records.
    This ensures each provider has unique CNAME and TXT values.
    """
    unique_string = f"provider-{provider_id}-{settings.SECRET_KEY[:10]}"
    hash_object = hashlib.sha256(unique_string.encode())
    return hash_object.hexdigest()[:12]


def get_dns_config_for_provider(provider):
    """
    Get the complete DNS configuration required for a provider's custom domain.
    Each provider gets unique records based on their provider ID.
    
    Returns:
        dict: Contains all DNS record information for the provider
    """
    if not provider.custom_domain:
        return None
    
    # Extract domain parts
    domain = provider.custom_domain
    domain_parts = domain.split('.')
    
    # Determine subdomain and root domain
    # Root domain = only 2 parts (e.g., urbanunit.in)
    # Subdomain = more than 2 parts (e.g., book.urbanunit.in)
    is_root_domain = len(domain_parts) == 2
    
    if len(domain_parts) > 2:
        subdomain = domain_parts[0]
        root_domain = '.'.join(domain_parts[1:])
    else:
        subdomain = '@'
        root_domain = domain
    
    # Generate unique provider identifier for DNS
    provider_unique_id = generate_provider_unique_id(provider.id)
    
    # CNAME target - should point to the HOSTING server (DigitalOcean App Platform)
    cname_target = getattr(settings, 'HOSTING_DOMAIN', settings.DEFAULT_DOMAIN)
    
    # TXT verification record - unique per provider
    txt_record_name = f"_booking-verify"
    txt_record_value = provider.domain_verification_code
    
    # Alternative: Provider-specific TXT name for multi-provider setup
    txt_record_name_unique = f"_bv-{provider_unique_id}"
    
    # For root domains, we need different instructions
    # Root domains cannot have CNAME records (DNS limitation)
    # Cloudflare uses "CNAME Flattening" to handle this
    if is_root_domain:
        record_type = 'CNAME (Flattened)'
        record_note = 'Cloudflare will automatically flatten this CNAME to A records'
    else:
        record_type = 'CNAME'
        record_note = 'Standard CNAME record'
    
    return {
        'provider_id': provider.id,
        'provider_unique_id': provider_unique_id,
        'full_domain': domain,
        'subdomain': subdomain,
        'root_domain': root_domain,
        'is_root_domain': is_root_domain,
        'cname': {
            'name': subdomain,
            'target': cname_target,
            'type': record_type,
            'note': record_note,
            'proxy_status': 'Proxied (Orange)',
            'description': f'Points your domain to our booking server'
        },
        'txt': {
            'name': txt_record_name,
            'value': txt_record_value,
            'proxy_status': 'DNS Only (Grey)',
            'description': 'Verifies domain ownership'
        },
        'txt_alternative': {
            'name': txt_record_name_unique,
            'value': txt_record_value,
            'proxy_status': 'DNS Only (Grey)',
            'description': 'Alternative verification record (provider-specific)'
        },
        'instructions': get_dns_instructions(subdomain, cname_target, txt_record_name, txt_record_value, is_root_domain)
    }


def get_dns_instructions(subdomain, cname_target, txt_name, txt_value, is_root_domain=False):
    """Generate human-readable DNS setup instructions."""
    if is_root_domain:
        return {
            'step1': 'Go to Cloudflare Dashboard → Select your domain → DNS',
            'step2': f'Add CNAME record: Name="@", Target="{cname_target}"',
            'step2_note': 'Cloudflare will automatically flatten this to A records (CNAME Flattening)',
            'step3': f'Add TXT record: Name="{txt_name}", Value="{txt_value}"',
            'step4': 'IMPORTANT: Enable Cloudflare proxy (orange cloud) - Required for root domains!',
            'step5': 'Set SSL/TLS encryption mode to "Full (Strict)"',
            'step6': 'Wait for DNS propagation (5 mins to 24 hours)',
            'step7': 'Click "Verify Domain" button to complete setup'
        }
    else:
        return {
            'step1': 'Go to your DNS provider (Cloudflare recommended)',
            'step2': f'Add CNAME record: Name="{subdomain}", Target="{cname_target}"',
            'step3': f'Add TXT record: Name="{txt_name}", Value="{txt_value}"',
            'step4': 'Enable Cloudflare proxy (orange cloud) for CNAME',
            'step5': 'Set SSL/TLS encryption mode to "Full (Strict)"',
            'step6': 'Wait for DNS propagation (5 mins to 24 hours)',
            'step7': 'Click "Verify Domain" button to complete setup'
        }

def verify_domain_dns(domain, expected_cname=None, expected_txt=None):
    """
    Verify DNS records for domain ownership.
    Works with Cloudflare proxied domains.
    
    Args:
        domain (str): The domain to verify
        expected_cname (str, optional): Expected CNAME value
        expected_txt (str, optional): Expected TXT record value for verification
        
    Returns:
        dict: Verification results with status and messages
    """
    results = {
        'success': False,
        'cname_verified': False,
        'txt_verified': False,
        'a_record_found': False,
        'is_root_domain': False,
        'messages': []
    }
    
    # Extract root domain for TXT record lookup
    # e.g., www.urbanunit.in -> urbanunit.in
    domain_parts = domain.split('.')
    is_root_domain = len(domain_parts) == 2
    results['is_root_domain'] = is_root_domain
    
    if len(domain_parts) > 2:
        root_domain = '.'.join(domain_parts[-2:])  # Get last 2 parts (urbanunit.in)
    else:
        root_domain = domain
    
    try:
        # Check for CNAME or A record (Cloudflare may return A records for proxied domains)
        if expected_cname:
            try:
                # First try CNAME
                cname_records = dns.resolver.resolve(domain, 'CNAME')
                cname_values = [str(r.target).rstrip('.') for r in cname_records]
                
                if expected_cname in cname_values or any(expected_cname in cv for cv in cname_values):
                    results['cname_verified'] = True
                    results['messages'].append('CNAME record is correctly configured.')
                else:
                    results['messages'].append(f'CNAME points to {cname_values}, expected {expected_cname}')
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                # If no CNAME, check for A record (Cloudflare proxy flattens CNAME to A)
                try:
                    a_records = dns.resolver.resolve(domain, 'A')
                    if a_records:
                        results['a_record_found'] = True
                        results['cname_verified'] = True  # Accept A record as valid (Cloudflare proxy)
                        a_ips = [str(r) for r in a_records]
                        results['messages'].append(f'A record found: {", ".join(a_ips)} (Cloudflare proxy detected).')
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                    if is_root_domain:
                        results['messages'].append(f'No A record found for root domain {domain}. In Cloudflare, add CNAME with Name="@" and Target="{expected_cname}" with Proxy ON.')
                    else:
                        results['messages'].append('No CNAME or A record found for ' + domain)
            except dns.resolver.NoNameservers:
                results['messages'].append('DNS servers not responding.')
        
        # Verify TXT record if expected_txt is provided
        # Check multiple possible locations for the TXT record
        if expected_txt:
            txt_locations = [
                f"_booking-verify.{root_domain}",      # _booking-verify.urbanunit.in (most common)
                f"_booking-verify.{domain}",           # _booking-verify.www.urbanunit.in
                root_domain,                            # urbanunit.in (main domain TXT)
                domain,                                 # www.urbanunit.in (subdomain TXT)
            ]
            
            txt_found = False
            for txt_domain in txt_locations:
                if txt_found:
                    break
                try:
                    txt_records = dns.resolver.resolve(txt_domain, 'TXT')
                    txt_values = []
                    for r in txt_records:
                        for s in r.strings:
                            txt_values.append(s.decode('utf-8'))
                    
                    if expected_txt in txt_values:
                        results['txt_verified'] = True
                        results['messages'].append(f'TXT verification record found at {txt_domain}.')
                        txt_found = True
                        break
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                    continue
                except Exception:
                    continue
            
            if not txt_found:
                results['messages'].append(f'TXT record not found. Create TXT record with name "_booking-verify" at {root_domain}')
        
        # Determine overall success
        # Option 1: CNAME/A record verified + TXT verified = Success
        # Option 2: For Cloudflare proxied (A record), TXT verification is sufficient
        # Option 3: For root domains with TXT verified, we trust ownership
        if results['cname_verified'] and results['txt_verified']:
            results['success'] = True
        elif results['a_record_found'] and results['txt_verified']:
            results['success'] = True
            results['messages'].append('Verified via Cloudflare proxy with TXT record.')
        elif results['txt_verified'] and is_root_domain:
            # For root domains, if TXT is verified, we can trust ownership
            # The CNAME might show as A record due to Cloudflare flattening
            results['success'] = True
            results['messages'].append('Root domain verified via TXT record. Please ensure CNAME is configured in Cloudflare with proxy enabled.')
        elif results['cname_verified'] and not expected_txt:
            results['success'] = True
        
        return results
        
    except Exception as e:
        results['messages'].append(f'Error during DNS verification: {str(e)}')
        return results

def setup_custom_domain(provider, domain, domain_type):
    """
    Set up a custom domain for a service provider.
    Each provider gets a unique verification code for their domain.
    
    Args:
        provider (ServiceProvider): The service provider to set up the domain for
        domain (str): The custom domain (e.g., 'www.example.com' or 'salon.example.com')
        domain_type (str): Type of domain ('subdomain' or 'domain')
        
    Returns:
        tuple: (success: bool, message: str, verification_code: str)
    """
    # Validate domain type
    if domain_type not in ['subdomain', 'domain']:
        return False, 'Invalid domain type. Must be either "subdomain" or "domain".', ''
    
    # Check if domain is already in use
    if ServiceProvider.objects.filter(custom_domain=domain).exclude(pk=provider.pk).exists():
        return False, 'This domain is already in use by another account.', ''
    
    # Generate unique verification code for this provider
    # Format: booking-verify-{provider_unique_id}-{random_string}
    provider_unique_id = generate_provider_unique_id(provider.id)
    verification_code = f'bv-{provider_unique_id}-{generate_verification_code(8)}'
    
    # Update provider with domain info
    provider.custom_domain = domain
    provider.custom_domain_type = domain_type
    provider.domain_verified = False
    provider.domain_verification_code = verification_code
    provider.domain_added_at = timezone.now()
    provider.save()
    
    return True, 'Domain setup initiated. Please verify ownership by adding the required DNS records.', verification_code

def verify_domain_ownership(provider):
    """
    Verify domain ownership by checking DNS records.
    
    Args:
        provider (ServiceProvider): The service provider with domain to verify
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if not provider.custom_domain or not provider.domain_verification_code:
        return False, 'No domain or verification code found.'
    
    # Use HOSTING_DOMAIN as the expected CNAME target
    expected_cname = getattr(settings, 'HOSTING_DOMAIN', settings.DEFAULT_DOMAIN)
    
    # For subdomains, we only need to verify CNAME
    if provider.custom_domain_type == 'subdomain':
        result = verify_domain_dns(
            domain=provider.custom_domain,
            expected_cname=expected_cname,
            expected_txt=provider.domain_verification_code
        )
    else:
        # For full domains, we need both CNAME and TXT verification
        result = verify_domain_dns(
            domain=provider.custom_domain,
            expected_cname=expected_cname,
            expected_txt=provider.domain_verification_code
        )
    
    if result['success']:
        # Update provider with verification status
        provider.domain_verified = True
        provider.ssl_enabled = True  # Auto-enable SSL for verified domains
        provider.save()
        return True, 'Domain verified successfully! SSL will be enabled shortly.'
    else:
        return False, 'Domain verification failed. ' + ' '.join(result['messages'])
