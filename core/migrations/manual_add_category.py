from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),  # This should be your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='category',
            field=models.CharField(choices=[('research', 'Research Paper'), ('journal', 'Journal Article'), ('projects', 'Project')], default='journal', max_length=20),
        ),
    ] 