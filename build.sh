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
pip install -r requirements.txt

# Collect static files locally to test
echo "📦 Collecting static files..."
python manage.py collectstatic --no-input

# Check for migrations
echo "🔍 Checking for pending migrations..."
python manage.py makemigrations --check --dry-run


# Apply database migrations
python manage.py migrate

# Create superuser if it doesn't exist (optional - you can remove this)
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'esa.kenyattauniv@gmail.com', 'Nairobi100!') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell 
