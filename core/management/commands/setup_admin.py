from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserRole, UserProfile
from django.db.utils import IntegrityError

class Command(BaseCommand):
    help = 'Set up admin user and default roles for ESA-KU'

    def handle(self, *args, **options):
        self.stdout.write('Setting up ESA-KU admin and roles...')
        
        # Create default roles
        self.create_default_roles()
        
        # Create admin user
        self.create_admin_user()
        
        self.stdout.write(self.style.SUCCESS('Setup complete!'))
    
    def create_default_roles(self):
        """Create the default roles in the system"""
        self.stdout.write('Creating default roles...')
        
        # Admin role - full permissions
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
                'can_post_resources': False,
                'is_admin': False,
                'can_manage_permissions': False
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
                'can_post_resources': False,
                'is_admin': False,
                'can_manage_permissions': False
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
                'can_post_resources': True,
                'is_admin': False,
                'can_manage_permissions': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created role: {resource_role.name}'))
        else:
            self.stdout.write(f'Role already exists: {resource_role.name}')
        
        # Vendor role
        vendor_role, created = UserRole.objects.get_or_create(
            name='Vendor',
            defaults={
                'description': 'Can add and manage their own products in the store',
                'can_post_events': False,
                'can_post_store_items': True,
                'can_post_resources': False,
                'is_admin': False,
                'can_manage_permissions': False
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created role: {vendor_role.name}'))
        else:
            self.stdout.write(f'Role already exists: {vendor_role.name}')
    
    def create_admin_user(self):
        """Create the main admin user with specified credentials"""
        self.stdout.write('Creating admin user...')
        
        # Admin credentials
        admin_email = 'esa.kenyattauniv@gmail.com'
        admin_username = 'esa_admin'
        admin_password = 'Nairobi100'
        
        # Create or get admin user
        try:
            admin_user, created = User.objects.get_or_create(
                email=admin_email,
                defaults={
                    'username': admin_username,
                    'is_staff': True,
                    'is_superuser': True,
                    'first_name': 'ESA',
                    'last_name': 'Administrator'
                }
            )
            
            if created:
                admin_user.set_password(admin_password)
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_email}'))
            else:
                self.stdout.write(f'Admin user already exists: {admin_email}')
                
            # Create or update admin profile
            try:
                # Get the admin role
                admin_role = UserRole.objects.get(name='ESA Admin')
                
                admin_profile, profile_created = UserProfile.objects.get_or_create(
                    user=admin_user,
                    defaults={
                        'student_id': 'ESA-ADMIN',
                        'department': 'Administration',
                        'year_of_study': 4,
                        'bio': 'ESA-KU Administrator',
                        'phone_number': '0712345678',
                        'role': admin_role,
                        'custom_permissions': False,
                        'can_post_events': True,
                        'can_post_store_items': True,
                        'can_post_resources': True,
                    }
                )
                
                if not profile_created:
                    # Update the role and permissions
                    admin_profile.role = admin_role
                    admin_profile.save()
                    self.stdout.write(f'Updated admin profile for: {admin_email}')
                else:
                    self.stdout.write(self.style.SUCCESS(f'Created admin profile for: {admin_email}'))
                    
            except UserRole.DoesNotExist:
                self.stdout.write(self.style.ERROR('Admin role not found. Make sure to run create_default_roles first.'))
                
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}')) 