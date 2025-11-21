from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import UserProfile, Membership


class Command(BaseCommand):
    help = 'Restore user data from backup'

    def handle(self, *args, **options):
        self.stdout.write('='*70)
        self.stdout.write('RESTORING USER DATA')
        self.stdout.write('='*70)
        
        users_data = [
            {
                'username': 'Amos',
                'email': '5936.2023@students.ku.ac.ke',
                'student_id': 'J173/5936/2023',
                'membership_number': 'ESA-KU08196',
                'department': 'Not specified',
                'year': 1,
                'status': 'active',
                'expiry': '2026-11-16'
            },
            {
                'username': 'Humphery',
                'email': '1390.2025@students.ku.ac.ke',
                'student_id': 'J79/1390/2025',
                'membership_number': 'ESA-KU73237',
                'department': 'Not specified',
                'year': 1,
                'status': 'active',
                'expiry': '2026-11-16'
            },
            {
                'username': 'Jamesmwangy',
                'email': 'mjorogejames794@gmail.com',
                'student_id': 'J76/9621/2025',
                'membership_number': 'ESA-KU97928',
                'department': 'Mechanical engineering',
                'year': 1,
                'status': 'active',
                'expiry': '2026-11-16'
            },
            {
                'username': 'Jeangugi',
                'email': '8661.2024@students.ku.ac.ke',
                'student_id': 'J23/8661/2024',
                'membership_number': None,
                'department': 'Not specified',
                'year': 1,
                'status': 'inactive',
                'expiry': None
            },
            {
                'username': 'Victor',
                'email': '9156.2024@students.ku.ac.ke',
                'student_id': 'J76/9156/2024',
                'membership_number': 'ESA-KU77983',
                'department': 'Not specified',
                'year': 1,
                'status': 'active',
                'expiry': '2026-11-18'
            },
            {
                'username': 'auka.esther',
                'email': '14518.2021@students.ku.ac.kr',
                'student_id': 'J76S/14518/2021',
                'membership_number': 'ESA-KU03801',
                'department': 'Mechanical Engineering',
                'year': 4,
                'status': 'active',
                'expiry': '2026-11-16'
            },
            {
                'username': 'doris_mutindi',
                'email': '4088.2021@students.ku.ac.ke',
                'student_id': 'J25/4088/2021',
                'membership_number': 'ESA-KU46586',
                'department': 'Agricultural and biosystems engineering',
                'year': 5,
                'status': 'active',
                'expiry': '2026-11-18'
            },
            {
                'username': 'dalton',
                'email': 'daltonomondi588@gmail.com',
                'first_name': 'Dalton',
                'last_name': 'Omondi',
                'student_id': 'J174/6153/2023',
                'membership_number': 'ESA-2025-EQGB5B',
                'department': 'Electrical and electronics engineering',
                'year': 3,
                'status': 'active',
                'expiry': '2026-07-26',
                'phone': '0793632858',
                'is_staff': True,
                'is_superuser': True
            },
            {
                'username': 'esa-admin',
                'email': 'esa.kenyattauniv@gmail.com',
                'first_name': 'ESA-KU',
                'last_name': 'admin',
                'student_id': 'STU00008',
                'membership_number': 'ESA-2025-4ROWFJ',
                'department': 'Not specified',
                'year': 1,
                'status': 'active',
                'expiry': '2026-11-16',
                'is_staff': True,
                'is_superuser': True
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for user_data in users_data:
            username = user_data['username']
            email = user_data['email']
            
            # 1. Create or Get User
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                    'is_staff': user_data.get('is_staff', False),
                    'is_superuser': user_data.get('is_superuser', False),
                }
            )
            
            if created:
                user.set_password('ChangeMe123!')
                user.save()
                action = "Created"
                created_count += 1
            else:
                action = "Updated"
                updated_count += 1

            # 2. Get or Create Profile (Safe against signals)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            
            # 3. Update Profile Fields
            profile.student_id = user_data['student_id']
            profile.department = user_data['department']
            profile.year_of_study = user_data['year']
            profile.phone_number = user_data.get('phone', '')
            profile.membership_number = user_data['membership_number']
            profile.membership_status = user_data['status']
            profile.membership_expiry = user_data['expiry']
            profile.save()
            
            # 4. Create/Update Membership if active
            if user_data['status'] == 'active' and user_data['membership_number']:
                expiry_date = timezone.datetime.strptime(user_data['expiry'], '%Y-%m-%d').date() if user_data['expiry'] else None
                
                if expiry_date:
                    Membership.objects.get_or_create(
                        user=user,
                        defaults={
                            'plan_type': 'other_students',
                            'amount': 300,
                            'payment_method': 'manual',
                            'status': 'completed',
                            'is_active': True,
                            'start_date': timezone.now() - timedelta(days=30),
                            'end_date': expiry_date,
                            'membership_number': user_data['membership_number']
                        }
                    )
            
            self.stdout.write(self.style.SUCCESS(f'✓ {action}: {username} ({email})'))
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write('SUMMARY')
        self.stdout.write('='*70)
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write('\n⚠️  DEFAULT PASSWORD: ChangeMe123!')
        self.stdout.write('='*70)
