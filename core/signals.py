from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from .email_service import EmailService

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Send a welcome email when a new user is created
    
    Args:
        sender: The model class that sent the signal
        instance: The instance being saved
        created: Boolean indicating if this is a new instance
    """
    # Only send welcome email on new user creation
    if created and instance.email:
        transaction.on_commit(lambda: EmailService.send_welcome_email(instance))
