from django.db import migrations

def add_sample_communities(apps, schema_editor):
    Community = apps.get_model('core', 'Community')
    
    communities = [
        {
            'name': 'IEEE-KU',
            'slug': 'ieee-ku',
            'description': 'The IEEE Student Branch at Kenyatta University promotes technical innovation and excellence for the benefit of humanity. We organize workshops, technical talks, and networking events for engineering students.',
            'website': 'https://ieee.ku.ac.ke',
            'email': 'ieee@ku.ac.ke',
            'facebook': 'https://facebook.com/ieeeku',
            'twitter': 'https://twitter.com/ieeeku',
            'instagram': 'https://instagram.com/ieeeku',
            'linkedin': 'https://linkedin.com/company/ieee-ku',
            'is_active': True
        },
        {
            'name': 'ESA Women in Engineering',
            'slug': 'esa-wie',
            'description': 'ESA-WIE is dedicated to promoting women engineers and scientists, and inspiring girls around the world to follow their academic interests in a career in engineering.',
            'website': 'https://esa.ku.ac.ke/wie',
            'email': 'wie@esa.ku.ac.ke',
            'facebook': 'https://facebook.com/esa-wie-ku',
            'twitter': 'https://twitter.com/esa_wie_ku',
            'instagram': 'https://instagram.com/esa_wie_ku',
            'linkedin': 'https://linkedin.com/company/esa-wie-ku',
            'is_active': True
        },
        {
            'name': 'ACES',
            'slug': 'aces',
            'description': 'The Association of Computer Engineering Students (ACES) focuses on computer engineering and technology. We organize coding competitions, hackathons, and tech workshops.',
            'website': 'https://aces.ku.ac.ke',
            'email': 'aces@ku.ac.ke',
            'facebook': 'https://facebook.com/aces-ku',
            'twitter': 'https://twitter.com/aces_ku',
            'instagram': 'https://instagram.com/aces_ku',
            'linkedin': 'https://linkedin.com/company/aces-ku',
            'is_active': True
        },
        {
            'name': 'SPE',
            'slug': 'spe',
            'description': 'The Society of Petroleum Engineers Student Chapter at Kenyatta University provides opportunities for students to learn about the oil and gas industry through technical presentations and field trips.',
            'website': 'https://spe.ku.ac.ke',
            'email': 'spe@ku.ac.ke',
            'facebook': 'https://facebook.com/spe-ku',
            'twitter': 'https://twitter.com/spe_ku',
            'instagram': 'https://instagram.com/spe_ku',
            'linkedin': 'https://linkedin.com/company/spe-ku',
            'is_active': True
        },
        {
            'name': 'IEEE Photonics',
            'slug': 'ieee-photonics',
            'description': 'The IEEE Photonics Society Student Chapter focuses on optics and photonics research and applications. We organize workshops and seminars on cutting-edge photonics technologies.',
            'website': 'https://photonics.ku.ac.ke',
            'email': 'photonics@ku.ac.ke',
            'facebook': 'https://facebook.com/ieee-photonics-ku',
            'twitter': 'https://twitter.com/ieee_photonics_ku',
            'instagram': 'https://instagram.com/ieee_photonics_ku',
            'linkedin': 'https://linkedin.com/company/ieee-photonics-ku',
            'is_active': True
        },
        {
            'name': 'Pivot Club',
            'slug': 'pivot-club',
            'description': 'The Pivot Club is dedicated to fostering innovation and entrepreneurship among engineering students. We organize startup workshops, pitch competitions, and networking events.',
            'website': 'https://pivot.ku.ac.ke',
            'email': 'pivot@ku.ac.ke',
            'facebook': 'https://facebook.com/pivot-club-ku',
            'twitter': 'https://twitter.com/pivot_club_ku',
            'instagram': 'https://instagram.com/pivot_club_ku',
            'linkedin': 'https://linkedin.com/company/pivot-club-ku',
            'is_active': True
        }
    ]
    
    for community_data in communities:
        Community.objects.create(**community_data)

def remove_sample_communities(apps, schema_editor):
    Community = apps.get_model('core', 'Community')
    Community.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_community'),
    ]

    operations = [
        migrations.RunPython(add_sample_communities, remove_sample_communities),
    ] 