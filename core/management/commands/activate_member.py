from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import Membership, UserProfile


class Command(BaseCommand):
    help = 'Activate membership for a user by username or email'

    def add_arguments(self, parser):
        parser.add_argument('identifier', type=str, help='Username or email of the user')
        parser.add_argument('--plan', type=str, default='other_students', 
                          help='Membership plan type (default: other_students)')
        parser.add_argument('--amount', type=int, default=300, 
                          help='Membership amount (default: 300)')

    def handle(self, *args, **options):
        identifier = options['identifier']
        plan_type = options['plan']
        amount = options['amount']
        
        # Find user
        try:
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{identifier}" not found'))
            return
        
        # Check if user has a profile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'Creating profile for {user.username}'))
            profile = UserProfile.objects.create(
                user=user,
                student_id=f"USER{user.id:04d}",
                department="Not specified",
                year_of_study=1,
                bio=""
            )
        
        # Find or create membership
        membership = Membership.objects.filter(user=user).order_by('-created_at').first()
        
        if membership:
            self.stdout.write(f'Found existing membership: {membership}')
            if membership.is_active:
                self.stdout.write(self.style.WARNING(f'Membership is already active'))
                self.stdout.write(f'  Status: {membership.status}')
                self.stdout.write(f'  Start: {membership.start_date}')
                self.stdout.write(f'  End: {membership.end_date}')
            else:
                self.stdout.write(self.style.WARNING(f'Activating existing membership...'))
                membership.activate()
                self.stdout.write(self.style.SUCCESS(f'✓ Membership activated!'))
        else:
            self.stdout.write(self.style.WARNING(f'No membership found. Creating new one...'))
            membership = Membership.objects.create(
                user=user,
                plan_type=plan_type,
                amount=amount,
                payment_method='manual',
                status='completed',
                is_active=True,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=365)
            )
            
            if not membership.membership_number:
                membership.membership_number = membership.generate_membership_number()
                membership.save()
            
            self.stdout.write(self.style.SUCCESS(f'✓ New membership created and activated!'))
        
        # Update profile
        profile.membership_status = 'active'
        profile.membership_expiry = membership.end_date.date() if membership.end_date else None
        if not profile.membership_number:
            profile.membership_number = membership.membership_number
        profile.save()
        
        self.stdout.write(self.style.SUCCESS('\n=== Membership Details ==='))
        self.stdout.write(f'User: {user.username} ({user.get_full_name() or "No name"})')
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'Membership Number: {membership.membership_number}')
        self.stdout.write(f'Plan: {membership.get_plan_type_display()}')
        self.stdout.write(f'Status: {membership.status}')
        self.stdout.write(f'Active: {membership.is_active}')
        self.stdout.write(f'Start Date: {membership.start_date}')
        self.stdout.write(f'End Date: {membership.end_date}')
        self.stdout.write(f'Profile Status: {profile.membership_status}')
        self.stdout.write(f'Profile Expiry: {profile.membership_expiry}')

