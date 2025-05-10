from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserRole, UserProfile
from django.db.utils import IntegrityError

class Command(BaseCommand):
    help = 'Set up default roles and ESA admin account'

    def handle(self, *args, **options):
        # Create default roles
        self.stdout.write('Creating default roles...')
        
        # Admin role
        admin_role, created = UserRole.objects.get_or_create(
            name='ESA Admin',
            defaults={
                'description': 'Full administrative access to all features',
                'can_post_events': True,
                'can_post_store_items': True,
                'can_post_resources': True,
                'is_admin': True,
                'can_manage_permissions': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created role: {admin_role.name}'))
        else:
            self.stdout.write(f'Role already exists: {admin_role.name}')
            
        # Event Manager role
        event_role, created = UserRole.objects.get_or_create(
            name='Event Manager',
            defaults={
                'description': 'Can create and manage events',
                'can_post_events': True,
                'can_post_store_items': False,
                'can_post_resources': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created role: {event_role.name}'))
        else:
            self.stdout.write(f'Role already exists: {event_role.name}')
            
        # Store Manager role
        store_role, created = UserRole.objects.get_or_create(
            name='Store Manager',
            defaults={
                'description': 'Can add and manage products in the store',
                'can_post_events': False,
                'can_post_store_items': True,
                'can_post_resources': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created role: {store_role.name}'))
        else:
            self.stdout.write(f'Role already exists: {store_role.name}')
            
        # Resource Manager role
        resource_role, created = UserRole.objects.get_or_create(
            name='Resource Manager',
            defaults={
                'description': 'Can upload and manage resources',
                'can_post_events': False,
                'can_post_store_items': False,
                'can_post_resources': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created role: {resource_role.name}'))
        else:
            self.stdout.write(f'Role already exists: {resource_role.name}')
            
        # Standard Member role
        member_role, created = UserRole.objects.get_or_create(
            name='Standard Member',
            defaults={
                'description': 'Regular ESA member with basic access',
                'can_post_events': False,
                'can_post_store_items': False,
                'can_post_resources': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created role: {member_role.name}'))
        else:
            self.stdout.write(f'Role already exists: {member_role.name}')
        
        # Create ESA admin account
        self.stdout.write('\nSetting up ESA admin account...')
        try:
            # Check if the ESA admin user already exists
            try:
                admin_user = User.objects.get(email='esa.kenyattauniv@gmail.com')
                self.stdout.write(f'ESA admin user already exists: {admin_user.username}')
            except User.DoesNotExist:
                # Create the admin user
                admin_user = User.objects.create_user(
                    username='esa_admin',
                    email='esa.kenyattauniv@gmail.com',
                    password='Nairobi100'
                )
                admin_user.first_name = 'ESA'
                admin_user.last_name = 'Admin'
                admin_user.is_staff = True  # Give access to admin panel
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f'Created ESA admin user: {admin_user.username}'))
            
            # Set up or update the admin user profile
            try:
                admin_profile = UserProfile.objects.get(user=admin_user)
                admin_profile.role = admin_role
                admin_profile.save()
                self.stdout.write(f'Updated ESA admin profile with admin role')
            except UserProfile.DoesNotExist:
                # Create profile for admin user
                admin_profile = UserProfile.objects.create(
                    user=admin_user,
                    student_id='ESA-ADMIN',
                    department='ESA Executive Committee',
                    role=admin_role,
                    membership_status='active'
                )
                self.stdout.write(self.style.SUCCESS(f'Created ESA admin profile with admin role'))
                
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error setting up ESA admin account: {e}'))
            
        self.stdout.write(self.style.SUCCESS('\nSetup complete!')) 