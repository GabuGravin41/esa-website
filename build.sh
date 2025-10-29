#!/usr/bin/env bash
# Exit on error
set -o errexit

# Create virtual environment if it doesn't exist
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p staticfiles
mkdir -p media

# Move to Django project directory
cd puddle

# Performance optimizations
echo "⚡ Setting up performance optimizations..."

# Create cache table for database caching
echo "🗄️  Setting up cache table..."
python manage.py createcachetable || echo "Cache table already exists"

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Collect static files with compression
echo "📦 Collecting and compressing static files..."
python manage.py collectstatic --no-input --clear

# Create superuser if it doesn't exist
echo "👤 Setting up admin user..."
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'esa.kenyattauniv@gmail.com', 'Nairobi100!') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

# Initialize admin users and roles
echo "🔐 Initializing admin users and permissions..."
echo "from core.models import initialize_admin_users; initialize_admin_users()" | python manage.py shell

# Warm up cache with frequently accessed data
echo "🔥 Warming up cache..."
echo "
from django.core.cache import cache
from core.models import Event, BlogPost, Announcement
from django.utils import timezone

# Pre-cache home page data
current_date = timezone.now().date()
events = list(Event.objects.filter(is_active=True, end_date__gte=current_date).order_by('start_date')[:3])
blog_posts = list(BlogPost.objects.filter(is_published=True).order_by('-created_at')[:2])
announcements = list(Announcement.objects.filter(is_active=True).exclude(expiry_date__lt=timezone.now())[:5])

cache_data = {
    'events': events,
    'blog_posts': blog_posts, 
    'announcements': announcements,
    'next_major_event': events[0] if events else None
}
cache.set('home_page_data', cache_data, 300)
print('✅ Cache warmed up successfully')
" | python manage.py shell

echo "✅ Build completed successfully with performance optimizations!"
