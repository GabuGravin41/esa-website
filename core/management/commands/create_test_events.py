import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import Event, UserProfile

class Command(BaseCommand):
    help = 'Creates sample events for testing'

    def handle(self, *args, **kwargs):
        # Ensure we have a default user for creating events
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.username}'))
        
        # Create or get the admin UserProfile
        admin_profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'student_id': 'ADMIN001',
                'department': 'Administration',
                'year_of_study': 4,
                'bio': 'Admin profile',
                'phone_number': '1234567890'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created admin profile for: {admin_user.username}'))
            
        # Create sample events
        now = timezone.now()
        events_data = [
            {
                'title': 'Advanced Robotics Workshop',
                'short_description': 'Hands-on workshop covering the latest advances in robotics engineering.',
                'description': """
                Join us for an interactive workshop where you'll learn about cutting-edge robotics technologies.
                
                This workshop will cover:
                - Fundamentals of robot kinematics and dynamics
                - Modern sensing and perception techniques
                - Programming autonomous behaviors
                - Hands-on experience with industrial robot arms
                
                All materials will be provided. No prior experience necessary, but basic programming knowledge is helpful.
                """,
                'category': 'workshop',
                'date': now + datetime.timedelta(days=15),
                'end_date': now + datetime.timedelta(days=15, hours=4),
                'location': 'Engineering Building, Room 305',
                'venue_type': 'physical',
                'capacity': 30,
                'price': 1000.00,
                'featured': True,
                'speaker': 'Prof. Sarah Johnson',
                'registration_deadline': now + datetime.timedelta(days=10),
                'status': 'upcoming',
            },
            {
                'title': 'National Engineering Conference 2024',
                'short_description': 'Annual gathering of engineering professionals, researchers, and students.',
                'description': """
                The premier engineering conference in the country, featuring keynote speeches, panel discussions, 
                research presentations, and networking opportunities.
                
                Key topics include:
                - Sustainable engineering solutions
                - Artificial intelligence in engineering
                - Climate change adaptation
                - Infrastructure resilience
                
                Join over 500 attendees from academia, industry, and government.
                """,
                'category': 'conference',
                'date': now + datetime.timedelta(days=30),
                'end_date': now + datetime.timedelta(days=32),
                'location': 'National Convention Center',
                'venue_type': 'hybrid',
                'capacity': 500,
                'price': 2500.00,
                'featured': True,
                'speaker': 'Multiple speakers',
                'registration_deadline': now + datetime.timedelta(days=20),
                'status': 'upcoming',
            },
            {
                'title': 'Career Fair: Engineering Opportunities',
                'short_description': 'Connect with top employers in the engineering field.',
                'description': """
                Meet representatives from leading engineering companies looking to hire talented graduates.
                
                Participating companies include:
                - National Infrastructure Authority
                - TechBuild Solutions
                - Global Engineering Consultants
                - EcoSystems Engineering
                
                Bring copies of your resume and be prepared for on-the-spot interviews.
                """,
                'category': 'career_fair',
                'date': now + datetime.timedelta(days=7),
                'end_date': now + datetime.timedelta(days=7, hours=8),
                'location': 'University Main Hall',
                'venue_type': 'physical',
                'capacity': 200,
                'price': 0.00,
                'featured': False,
                'speaker': '',
                'registration_deadline': now + datetime.timedelta(days=5),
                'status': 'upcoming',
            },
            {
                'title': 'Modern Construction Techniques',
                'short_description': 'Exploring innovative approaches to building design and construction.',
                'description': """
                This seminar explores cutting-edge construction methodologies that are changing the industry.
                
                Topics include:
                - Modular and prefabricated construction
                - Sustainable building materials
                - BIM (Building Information Modeling)
                - Smart building technologies
                
                Ideal for civil engineering students and construction professionals.
                """,
                'category': 'seminar',
                'date': now - datetime.timedelta(days=5),
                'end_date': now - datetime.timedelta(days=5, hours=3),
                'location': 'Civil Engineering Department, Room 110',
                'venue_type': 'physical',
                'capacity': 150,
                'price': 500.00,
                'featured': False,
                'speaker': 'Eng. Robert Chen',
                'status': 'completed',
            },
            {
                'title': 'Software Development Hackathon',
                'short_description': '48-hour coding challenge to develop solutions for community problems.',
                'description': """
                Put your programming skills to the test in this intensive hackathon.
                
                Challenge:
                Develop software solutions that address challenges faced by local communities.
                
                Teams of 2-4 members will compete for prizes totaling over 100,000 KSH.
                All programming languages and platforms are welcome.
                """,
                'category': 'competition',
                'date': now - datetime.timedelta(days=15),
                'end_date': now - datetime.timedelta(days=14),
                'location': 'Computer Science Building',
                'venue_type': 'physical',
                'capacity': 100,
                'price': 200.00,
                'featured': False,
                'speaker': '',
                'status': 'completed',
            },
            {
                'title': 'Field Trip: Renewable Energy Plant',
                'short_description': 'Visit to a state-of-the-art solar and wind power facility.',
                'description': """
                Experience firsthand the operations of a modern renewable energy facility.
                
                The tour will include:
                - Overview of plant operations
                - Exploration of solar array fields
                - Wind turbine technology demonstration
                - Q&A with plant engineers
                
                Transportation provided from campus. Lunch included.
                """,
                'category': 'field_trip',
                'date': now + datetime.timedelta(days=21),
                'end_date': now + datetime.timedelta(days=21, hours=6),
                'location': 'GreenPower Energy Plant, 50km North of campus',
                'venue_type': 'physical',
                'capacity': 40,
                'price': 800.00,
                'featured': False,
                'speaker': 'Plant Director',
                'registration_deadline': now + datetime.timedelta(days=18),
                'status': 'upcoming',
            },
        ]
        
        event_count = 0
        for event_data in events_data:
            event, created = Event.objects.get_or_create(
                title=event_data['title'],
                defaults={**event_data, 'created_by': admin_user}
            )
            
            if created:
                event_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created event: {event.title}'))
            
        self.stdout.write(self.style.SUCCESS(f'Successfully created {event_count} test events')) 