from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import initialize_admin_users


class Command(BaseCommand):
    help = 'Initialize default admin users for the ESA platform'

    def handle(self, *args, **kwargs):
        # Check existing users
        admin_exists = User.objects.filter(username='admin').exists()
        moderator_exists = User.objects.filter(username='moderator').exists()
        
        if admin_exists and moderator_exists:
            self.stdout.write(self.style.WARNING('Admin users already exist. Skipping initialization.'))
            return
        
        # Initialize admin users
        initialize_admin_users()
        
        # Output success message
        self.stdout.write(self.style.SUCCESS('Successfully initialized admin users!'))
        self.stdout.write('Admin credentials:')
        self.stdout.write('  Username: admin')
        self.stdout.write('  Password: adminpassword123')
        self.stdout.write('')
        self.stdout.write('Moderator credentials:')
        self.stdout.write('  Username: moderator')
        self.stdout.write('  Password: moderatorpassword123')