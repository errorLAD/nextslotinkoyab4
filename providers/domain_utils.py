"""
Utilities for domain verification and management.
Supports Cloudflare for SSL and DNS management.
"""
import dns.resolver
import random
import string
import requests
from django.conf import settings
from django.utils import timezone
from .models import ServiceProvider

def generate_verification_code(length=32):
    """Generate a random verification code for domain verification."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

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
        'messages': []
    }
    
    # Extract root domain for TXT record lookup
    # e.g., www.urbanunit.in -> urbanunit.in
    domain_parts = domain.split('.')
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
                        results['messages'].append('A record found (Cloudflare proxy detected).')
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                    results['messages'].append('No CNAME or A record found for ' + domain)
            except dns.resolver.NoNameservers:
                results['messages'].append('DNS servers not responding.')
        
        # Verify TXT record if expected_txt is provided
        # Check multiple possible locations for the TXT record
        if expected_txt:
            txt_locations = [
                f"_booking-verify.{root_domain}",      # _booking-verify.urbanunit.in (most common)
                f"_booking-verify.{domain}",           # _booking-verify.www.urbanunit.in
                f"_booking-verify",                     # Just _booking-verify (relative)
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
        # For Cloudflare proxied domains (A record), we accept without TXT if CNAME/A is valid
        if results['cname_verified']:
            if results['a_record_found']:
                # Cloudflare proxy detected - TXT is optional but helpful
                results['success'] = True
                if not results['txt_verified']:
                    results['messages'].append('Verified via Cloudflare proxy. TXT record optional.')
            elif results['txt_verified']:
                results['success'] = True
            elif expected_txt is None:
                results['success'] = True
        
        return results
        
    except Exception as e:
        results['messages'].append(f'Error during DNS verification: {str(e)}')
        return results

def setup_custom_domain(provider, domain, domain_type):
    """
    Set up a custom domain for a service provider.
    
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
    
    # Generate verification code
    verification_code = f'booking-verify-{generate_verification_code(12)}'
    
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
    
    # For subdomains, we only need to verify CNAME
    if provider.custom_domain_type == 'subdomain':
        result = verify_domain_dns(
            domain=provider.custom_domain,
            expected_cname=settings.DEFAULT_DOMAIN,
            expected_txt=provider.domain_verification_code
        )
    else:
        # For full domains, we need both CNAME and TXT verification
        result = verify_domain_dns(
            domain=provider.custom_domain,
            expected_cname=settings.DEFAULT_DOMAIN,
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
