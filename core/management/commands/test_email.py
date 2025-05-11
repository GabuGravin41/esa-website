from django.core.management.base import BaseCommand
from django.core.mail import send_mail, get_connection
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address to send test to')

    def handle(self, *args, **options):
        recipient = options['email'] or settings.ADMINS[0][1]
        
        self.stdout.write(self.style.WARNING(f'Email Configuration:'))
        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'Default From: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'Sending to: {recipient}')
        
        try:
            self.stdout.write(self.style.WARNING('\nAttempting to send email...'))
            
            # Try getting a connection first to check authentication
            connection = get_connection()
            connection.open()
            
            send_mail(
                subject='Test Email from ESA-KU',
                message='This is a test email from ESA-KU to verify email configuration.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
                connection=connection,
            )
            
            self.stdout.write(self.style.SUCCESS('Email sent successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error sending email: {str(e)}'))
            self.stdout.write('\nRecommended fixes:')
            
            if 'Authentication' in str(e):
                self.stdout.write('1. Check your EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in your .env file')
                self.stdout.write('2. If using Gmail, make sure you have an App Password (not your regular password)')
                self.stdout.write('   Create one at: https://myaccount.google.com/apppasswords')
                
            elif 'Connection refused' in str(e):
                self.stdout.write('1. Check your EMAIL_HOST and EMAIL_PORT settings')
                self.stdout.write('2. Make sure your firewall is not blocking outgoing SMTP connections')
                
            self.stdout.write('\nAlternative solutions:')
            self.stdout.write('1. For development, use the console backend:')
            self.stdout.write('   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend')
            
            sys.exit(1) 