from django.core.management.base import BaseCommand
from core.models import BlogPost
from django.db import connection

class Command(BaseCommand):
    help = 'Check fields in models'

    def handle(self, *args, **options):
        # Check BlogPost fields
        self.stdout.write("BlogPost model fields:")
        for field in BlogPost._meta.get_fields():
            self.stdout.write(f"- {field.name}")
        
        # Check database schema
        self.stdout.write("\nDatabase schema for core_blogpost table:")
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(core_blogpost)")
            for col in cursor.fetchall():
                self.stdout.write(f"- {col}") 