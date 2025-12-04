#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','booking_saas.settings')
django.setup()
from providers.models import ServiceProvider
for sp in ServiceProvider.objects.all():
    print(f"id={sp.id}, business_name={sp.business_name}, unique_booking_url={sp.unique_booking_url}, logo={sp.logo}")
