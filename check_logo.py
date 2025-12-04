#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booking_saas.settings')
django.setup()

from providers.models import ServiceProvider

sp = ServiceProvider.objects.first()
if sp:
    print(f"Logo field value: {sp.logo}")
    if sp.logo:
        print(f"Logo URL: {sp.logo.url}")
        print(f"Logo path: {sp.logo.path if sp.logo else 'N/A'}")
    else:
        print("Logo field is empty")
else:
    print("No service provider found")
