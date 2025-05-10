from django.core.management.base import BaseCommand
from core.models import initialize_admin_users

class Command(BaseCommand):
    help = 'Initialize admin users with hardcoded credentials'

    def handle(self, *args, **options):
        self.stdout.write('Creating admin users...')
        initialize_admin_users()
        self.stdout.write(self.style.SUCCESS('Admin users successfully created!'))
        self.stdout.write('You can now log in with:')
        self.stdout.write('  Username: admin')
        self.stdout.write('  Password: adminpassword123')
        self.stdout.write('OR')
        self.stdout.write('  Username: moderator')
        self.stdout.write('  Password: moderatorpassword123') 