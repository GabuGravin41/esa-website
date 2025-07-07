from django.core.management.base import BaseCommand
from core.models import Membership, UserProfile

class Command(BaseCommand):
    help = 'Ensure all user profiles have their membership number set if they have a completed membership.'

    def handle(self, *args, **options):
        updated = 0
        for membership in Membership.objects.filter(status='completed', is_active=True):
            try:
                profile = membership.user.profile
                if not profile.membership_number and membership.membership_number:
                    profile.membership_number = membership.membership_number
                    profile.save(update_fields=['membership_number'])
                    updated += 1
                    self.stdout.write(self.style.SUCCESS(f"Updated profile for {profile.user.username} with membership number {membership.membership_number}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating profile for user {membership.user}: {e}"))
        self.stdout.write(self.style.SUCCESS(f"Done. {updated} profiles updated."))
