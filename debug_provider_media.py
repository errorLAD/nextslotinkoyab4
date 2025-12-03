#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','booking_saas.settings')
django.setup()
from providers.models import ServiceProvider

def print_provider(p):
    print('-'*60)
    print(f'id={p.id} name={p.business_name!r} slug={p.unique_booking_url!r}')
    print(f'  logo: {p.logo.name if p.logo else None}')
    print(f'  profile_image: {p.profile_image.name if p.profile_image else None}')
    hero_list = list(p.hero_images.filter(is_active=True).order_by('display_order'))
    print(f'  hero_images_count(active): {len(hero_list)}')
    for h in hero_list:
        print(f'    - {h.id}: {h.image.name if h.image else None} (caption={h.caption})')
    team_list = list(p.team_members.filter(is_active=True).order_by('display_order'))
    print(f'  team_members_count(active): {len(team_list)}')
    for t in team_list:
        print(f'    - {t.id}: {t.photo.name if t.photo else None} (name={t.name})')
    testimonials = list(p.testimonials.filter(is_active=True).order_by('-date_added'))
    print(f'  testimonials_count(active): {len(testimonials)}')
    for tt in testimonials:
        print(f'    - {tt.id}: {tt.client_photo.name if tt.client_photo else None} (client={tt.client_name})')

for sp in ServiceProvider.objects.all().order_by('id'):
    print_provider(sp)

print('\nTo inspect a specific provider, run: python debug_provider_media.py | Select-String "id=3" -Context 0,5')
