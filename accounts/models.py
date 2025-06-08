from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import UserProfile
from threading import current_thread

# No custom models needed as we're using the built-in User model
# and UserProfile from the core app

# Use dispatch_uid to prevent duplicate signal registration
@receiver(post_save, sender=User, dispatch_uid="accounts_create_user_profile")
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for every new User"""
    print(f"Signal handler: User saved - {instance.username} (created: {created})")
    
    # Only run this if we're coming from the registration form
    # where we saved thread.student_id
    if created:
        thread = current_thread()
        student_id = getattr(thread, 'student_id', None)
        print(f"Student ID from thread: {student_id}")
        
        # Only continue if we have a student_id from the registration form
        if student_id:
            # Don't create a profile if it already exists
            if hasattr(instance, 'profile'):
                print(f"Profile already exists for user {instance}")
                return
                
            try:
                # Create the profile with the student_id from the form
                profile = UserProfile.objects.create(
                    user=instance,
                    student_id=student_id,
                    department="Not specified",
                    year_of_study=1,
                    bio="",
                    phone_number=""
                )
                print(f"Created profile for user {instance} with student ID {student_id}")
                print(f"Profile created: {profile}")
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
