from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Membership, UserProfile
from django.db import transaction


class Command(BaseCommand):
    help = 'Sync all active UserProfiles with Membership records'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview changes')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('='*70)
        self.stdout.write('MEMBERSHIP SYNC REPORT')
        self.stdout.write('='*70)
        
        active_profiles = UserProfile.objects.filter(membership_status='active').select_related('user')
        
        self.stdout.write(f'\nActive profiles: {active_profiles.count()}')
        self.stdout.write(f'Total membership records: {Membership.objects.count()}\n')
        
        created_count = 0
        activated_count = 0
        ok_count = 0
        
        for profile in active_profiles:
            user = profile.user
            membership = Membership.objects.filter(user=user).order_by('-created_at').first()
            
            if not membership:
                self.stdout.write(f'X {user.username}: NO membership record')
                
                if not dry_run:
                    membership = Membership.objects.create(
                        user=user,
                        plan_type='other_students',
                        amount=300,
                        payment_method='manual',
                        status='completed',
                        is_active=True,
                        start_date=timezone.now() - timedelta(days=30),
                        end_date=(profile.membership_expiry or (timezone.now().date() + timedelta(days=365)))
                    )
                    
                    if profile.membership_number:
                        membership.membership_number = profile.membership_number
                    else:
                        membership.membership_number = membership.generate_membership_number()
                        profile.membership_number = membership.membership_number
                    
                    membership.save()
                    
                    if not profile.membership_expiry:
                        profile.membership_expiry = membership.end_date.date()
                    profile.save(update_fields=['membership_number', 'membership_expiry'])
                    
                    self.stdout.write(f'  + Created: {membership.membership_number}')
                    created_count += 1
                else:
                    self.stdout.write('  -> Would create (dry-run)')
                    created_count += 1
                    
            elif not membership.is_active:
                self.stdout.write(f'! {user.username}: Inactive membership')
                
                if not dry_run:
                    membership.activate()
                    self.stdout.write(f'  + Activated: {membership.membership_number}')
                    activated_count += 1
                else:
                    self.stdout.write('  -> Would activate (dry-run)')
                    activated_count += 1
            else:
                self.stdout.write(f'OK {user.username}: {membership.membership_number}')
                ok_count += 1
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write('SUMMARY')
        self.stdout.write('='*70)
        self.stdout.write(f'Already OK: {ok_count}')
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Activated: {activated_count}')
        
        if dry_run:
            self.stdout.write('\nDRY RUN - No changes made')
        else:
            self.stdout.write(f'\nFixed {created_count + activated_count} memberships!')
        self.stdout.write('='*70)

