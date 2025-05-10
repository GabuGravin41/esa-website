from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for handling email operations"""
    
    @staticmethod
    def send_email(subject, recipient_list, template_name, context, from_email=None):
        """
        Send an email using a template
        
        Args:
            subject (str): Email subject
            recipient_list (list): List of email recipients
            template_name (str): Path to the email template
            context (dict): Context data for the template
            from_email (str, optional): Sender email. Defaults to settings.DEFAULT_FROM_EMAIL.
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            if from_email is None:
                from_email = settings.DEFAULT_FROM_EMAIL
                
            # Render HTML content
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user"""
        context = {
            'user': user,
            'site_name': 'ESA-KU',
        }
        
        return EmailService.send_email(
            subject="Welcome to ESA-KU",
            recipient_list=[user.email],
            template_name="core/emails/welcome_email.html",
            context=context,
        )
    
    @staticmethod
    def send_membership_confirmation(user, membership):
        """Send membership confirmation email"""
        context = {
            'user': user,
            'membership': membership,
            'site_name': 'ESA-KU',
        }
        
        return EmailService.send_email(
            subject="Your ESA-KU Membership",
            recipient_list=[user.email],
            template_name="core/emails/membership_confirmation.html",
            context=context,
        )
    
    @staticmethod
    def send_payment_confirmation(user, payment):
        """Send payment confirmation email"""
        context = {
            'user': user,
            'payment': payment,
            'site_name': 'ESA-KU',
        }
        
        return EmailService.send_email(
            subject="Payment Confirmation",
            recipient_list=[user.email],
            template_name="core/emails/payment_confirmation.html",
            context=context,
        )

def send_payment_confirmation_email(user, membership):
    """Helper function to send payment confirmation email"""
    return EmailService.send_payment_confirmation(user, membership)