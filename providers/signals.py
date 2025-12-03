"""
Signals for automatic provider profile creation, appointment tracking,
and automatic cleanup of old images when new ones are uploaded.
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from accounts.models import CustomUser
from providers.models import ServiceProvider, HeroImage, TeamMember, Testimonial
import os


def delete_file_if_exists(file_field):
    """Helper function to delete a file from storage if it exists."""
    if file_field and hasattr(file_field, 'path'):
        try:
            if os.path.isfile(file_field.path):
                os.remove(file_field.path)
                return True
        except Exception as e:
            print(f"Error deleting file {file_field.path}: {e}")
    return False


# =============================================
# ServiceProvider Image Cleanup Signals
# =============================================

@receiver(pre_save, sender=ServiceProvider)
def auto_delete_old_provider_images(sender, instance, **kwargs):
    """
    Automatically delete old logo and profile_image files when new ones are uploaded.
    """
    if not instance.pk:
        return  # New instance, nothing to delete
    
    try:
        old_instance = ServiceProvider.objects.get(pk=instance.pk)
    except ServiceProvider.DoesNotExist:
        return
    
    # Check if logo has changed
    if old_instance.logo and instance.logo != old_instance.logo:
        delete_file_if_exists(old_instance.logo)
    
    # Check if profile_image has changed
    if old_instance.profile_image and instance.profile_image != old_instance.profile_image:
        delete_file_if_exists(old_instance.profile_image)


@receiver(post_delete, sender=ServiceProvider)
def auto_delete_provider_images_on_delete(sender, instance, **kwargs):
    """
    Delete logo and profile_image files when ServiceProvider is deleted.
    """
    delete_file_if_exists(instance.logo)
    delete_file_if_exists(instance.profile_image)


# =============================================
# HeroImage Cleanup Signals
# =============================================

@receiver(pre_save, sender=HeroImage)
def auto_delete_old_hero_image(sender, instance, **kwargs):
    """
    Automatically delete old hero image file when a new one is uploaded.
    """
    if not instance.pk:
        return
    
    try:
        old_instance = HeroImage.objects.get(pk=instance.pk)
    except HeroImage.DoesNotExist:
        return
    
    if old_instance.image and instance.image != old_instance.image:
        delete_file_if_exists(old_instance.image)


@receiver(post_delete, sender=HeroImage)
def auto_delete_hero_image_on_delete(sender, instance, **kwargs):
    """
    Delete image file when HeroImage is deleted.
    """
    delete_file_if_exists(instance.image)


# =============================================
# TeamMember Photo Cleanup Signals
# =============================================

@receiver(pre_save, sender=TeamMember)
def auto_delete_old_team_photo(sender, instance, **kwargs):
    """
    Automatically delete old team member photo when a new one is uploaded.
    """
    if not instance.pk:
        return
    
    try:
        old_instance = TeamMember.objects.get(pk=instance.pk)
    except TeamMember.DoesNotExist:
        return
    
    if old_instance.photo and instance.photo != old_instance.photo:
        delete_file_if_exists(old_instance.photo)


@receiver(post_delete, sender=TeamMember)
def auto_delete_team_photo_on_delete(sender, instance, **kwargs):
    """
    Delete photo file when TeamMember is deleted.
    """
    delete_file_if_exists(instance.photo)


# =============================================
# Testimonial Photo Cleanup Signals
# =============================================

@receiver(pre_save, sender=Testimonial)
def auto_delete_old_testimonial_photo(sender, instance, **kwargs):
    """
    Automatically delete old testimonial client photo when a new one is uploaded.
    """
    if not instance.pk:
        return
    
    try:
        old_instance = Testimonial.objects.get(pk=instance.pk)
    except Testimonial.DoesNotExist:
        return
    
    if old_instance.client_photo and instance.client_photo != old_instance.client_photo:
        delete_file_if_exists(old_instance.client_photo)


@receiver(post_delete, sender=Testimonial)
def auto_delete_testimonial_photo_on_delete(sender, instance, **kwargs):
    """
    Delete client_photo file when Testimonial is deleted.
    """
    delete_file_if_exists(instance.client_photo)


# =============================================
# User Profile Signals (existing)
# =============================================

@receiver(post_save, sender=CustomUser)
def create_provider_profile(sender, instance, created, **kwargs):
    """
    Automatically create ServiceProvider profile when a provider user is created.
    """
    if created and instance.user_type == 'provider':
        # Don't create profile automatically - let user complete setup
        pass


@receiver(post_save, sender=CustomUser)
def save_provider_profile(sender, instance, **kwargs):
    """
    Save provider profile when user is saved.
    """
    if instance.user_type == 'provider' and hasattr(instance, 'provider_profile'):
        instance.provider_profile.save()
