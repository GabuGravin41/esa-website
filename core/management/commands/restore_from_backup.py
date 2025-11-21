from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = 'Restore database from backup_data.json file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='backup_data.json',
            help='Backup file to restore from'
        )

    def handle(self, *args, **options):
        backup_file = options['file']
        
        if not os.path.exists(backup_file):
            self.stdout.write(self.style.ERROR(f'Backup file not found: {backup_file}'))
            self.stdout.write('Available backup files:')
            for file in os.listdir('.'):
                if file.endswith('.json'):
                    self.stdout.write(f'  - {file}')
            return
        
        self.stdout.write('='*70)
        self.stdout.write('RESTORING FROM BACKUP')
        self.stdout.write('='*70)
        self.stdout.write(f'Backup file: {backup_file}')
        
        try:
            # Load the data
            call_command('loaddata', backup_file, verbosity=2)
            
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.SUCCESS('✓ RESTORE COMPLETED SUCCESSFULLY'))
            self.stdout.write('='*70)
            
        except Exception as e:
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.ERROR(f'✗ RESTORE FAILED: {str(e)}'))
            self.stdout.write('='*70)

