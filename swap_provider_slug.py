#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','booking_saas.settings')
django.setup()
from providers.models import ServiceProvider

def unique_slug(base_slug):
    # Ensure slug is unique by appending suffix if needed
    candidate = base_slug
    counter = 1
    while ServiceProvider.objects.filter(unique_booking_url=candidate).exists():
        candidate = f"{base_slug}-{counter}"
        counter += 1
    return candidate

old_slug = 'infrablue'
new_slug_owner = 'infrablue-1'  # provider that currently has the images

try:
    a = ServiceProvider.objects.get(unique_booking_url=old_slug)
except ServiceProvider.DoesNotExist:
    a = None

try:
    b = ServiceProvider.objects.get(unique_booking_url=new_slug_owner)
except ServiceProvider.DoesNotExist:
    b = None

print('Before change:')
for sp in ServiceProvider.objects.filter(unique_booking_url__in=[old_slug, new_slug_owner]):
    print(f'  id={sp.id} slug={sp.unique_booking_url} logo={sp.logo}')

if not b:
    print(f'Error: no provider found with slug {new_slug_owner}. Aborting.')
    raise SystemExit(1)

if a:
    # rename a to a safe unique slug
    new_a_slug = unique_slug(f"{a.unique_booking_url}-old-{a.id}")
    print(f'Renaming existing provider id={a.id} slug {a.unique_booking_url} -> {new_a_slug}')
    a.unique_booking_url = new_a_slug
    a.save()
else:
    print(f'No provider with slug {old_slug} found; proceeding to assign slug to target.')

# Now assign desired slug to provider b
print(f'Setting provider id={b.id} slug {b.unique_booking_url} -> {old_slug}')
b.unique_booking_url = old_slug
b.save()

print('\nAfter change:')
for sp in ServiceProvider.objects.filter(id__in=[s.id for s in ServiceProvider.objects.filter(unique_booking_url__in=[old_slug, new_a_slug if a else old_slug])]):
    print(f'  id={sp.id} slug={sp.unique_booking_url} logo={sp.logo}')

print('\nDone. Open the booking page at /appointments/book/infrablue/')
