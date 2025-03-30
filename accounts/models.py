from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import UserProfile

# No custom models needed as we're using the built-in User model
# and UserProfile from the core app

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for every new User"""
    if created:
        UserProfile.objects.create(
            user=instance,
            student_id=f"STU{instance.id:05d}",  # Format: STU00001, STU00002, etc.
            department="Not specified",
            year_of_study=1,
            bio="",
            phone_number=""
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile whenever the User is saved"""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        # Create a profile if it doesn't exist
        UserProfile.objects.create(
            user=instance,
            student_id=f"STU{instance.id:05d}",
            department="Not specified",
            year_of_study=1,
            bio="",
            phone_number=""
        )
