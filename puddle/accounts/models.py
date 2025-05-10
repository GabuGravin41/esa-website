from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import UserProfile
from threading import current_thread

# No custom models needed as we're using the built-in User model
# and UserProfile from the core app

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for every new User"""
    if created:
        # Check if a profile already exists (can happen if another signal created it)
        if hasattr(instance, 'profile'):
            return
            
        # Check if there's student_id in the current thread (from the form)
        thread = current_thread()
        student_id = getattr(thread, 'student_id', None)
        
        if not student_id:
            student_id = f"STU{instance.id:05d}"  # Default format if not provided
        
        try:
            # Use get_or_create to avoid duplicate creation
            UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    "student_id": student_id,
                    "department": "Not specified",
                    "year_of_study": 1,
                    "bio": "",
                    "phone_number": ""
                }
            )
        except Exception as e:
            # Log any errors but don't crash
            print(f"Error creating profile for user {instance}: {e}")
            pass

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile whenever the User is saved"""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        # Skip profile creation here - let the create_user_profile handle it
        pass
