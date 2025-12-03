#!/usr/bin/env python
import os
import shutil
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booking_saas.settings')
django.setup()

from providers.models import ServiceProvider, HeroImage, TeamMember, Testimonial
from django.conf import settings

media_root = settings.MEDIA_ROOT

def sanitize_filename(filename):
    """Sanitize filename by removing spaces and special characters."""
    if not filename:
        return filename
    name, ext = os.path.splitext(filename)
    name = name.replace(' ', '-')
    name = ''.join(c if c.isalnum() or c in '-_' else '' for c in name)
    return name + ext

def rename_file(old_path, new_path):
    """Safely rename a file."""
    old_full = os.path.join(media_root, old_path)
    new_full = os.path.join(media_root, new_path)
    
    if not os.path.exists(old_full):
        print(f"  ⚠️  File not found: {old_full}")
        return False
    
    if os.path.exists(new_full):
        print(f"  ⚠️  Target already exists: {new_full}")
        return False
    
    # Ensure directory exists for new file
    os.makedirs(os.path.dirname(new_full), exist_ok=True)
    
    try:
        shutil.move(old_full, new_full)
        print(f"  ✅ Renamed: {old_path} → {new_path}")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

print("Renaming files with spaces and special characters...\n")

# Process ServiceProvider logos and profile images
print("Processing ServiceProvider images...")
for sp in ServiceProvider.objects.all():
    if sp.logo:
        old_name = sp.logo.name
        new_name = f'provider_logos/{sp.id}_{sanitize_filename(os.path.basename(old_name))}'
        if old_name != new_name:
            if rename_file(old_name, new_name):
                sp.logo.name = new_name
                sp.save()
    
    if sp.profile_image:
        old_name = sp.profile_image.name
        new_name = f'profile_images/{sp.id}_{sanitize_filename(os.path.basename(old_name))}'
        if old_name != new_name:
            if rename_file(old_name, new_name):
                sp.profile_image.name = new_name
                sp.save()

# Process HeroImage images
print("\nProcessing HeroImage images...")
for hi in HeroImage.objects.all():
    if hi.image:
        old_name = hi.image.name
        new_name = f'hero_images/{hi.service_provider_id}_{hi.id}_{sanitize_filename(os.path.basename(old_name))}'
        if old_name != new_name:
            if rename_file(old_name, new_name):
                hi.image.name = new_name
                hi.save()

# Process TeamMember photos
print("\nProcessing TeamMember photos...")
for tm in TeamMember.objects.all():
    if tm.photo:
        old_name = tm.photo.name
        new_name = f'team_photos/{tm.service_provider_id}_{tm.id}_{sanitize_filename(os.path.basename(old_name))}'
        if old_name != new_name:
            if rename_file(old_name, new_name):
                tm.photo.name = new_name
                tm.save()

# Process Testimonial photos
print("\nProcessing Testimonial client photos...")
for t in Testimonial.objects.all():
    if t.client_photo:
        old_name = t.client_photo.name
        new_name = f'testimonial_photos/{t.service_provider_id}_{t.id}_{sanitize_filename(os.path.basename(old_name))}'
        if old_name != new_name:
            if rename_file(old_name, new_name):
                t.client_photo.name = new_name
                t.save()

print("\n✅ File renaming complete!")
