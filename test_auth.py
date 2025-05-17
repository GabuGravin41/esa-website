#!/usr/bin/env python3
import os
import sys

try:
    print("Starting test script...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.executable}")
    
    # Set up Django
    print("Setting up Django environment...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'puddle.settings')
    
    import django
    django.setup()
    print("Django setup successful!")
    
    # Now you can import Django models
    from django.contrib.auth.models import User
    from django.contrib.auth import authenticate
    
    # Test all users
    print("\n=== TESTING ALL USERS IN SYSTEM ===")
    users = User.objects.all()
    
    if not users:
        print("No users found in the database!")
    else:
        print(f"Found {users.count()} users in the database.")
        
        for user in users:
            print(f"\nUser: {user.username}")
            print(f"  ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Is active: {user.is_active}")
            print(f"  Last login: {user.last_login}")
            
    print("\nScript completed successfully!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Now you can import Django models
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def test_all_users():
    """Test authentication for all users in the system"""
    print("\n=== TESTING ALL USERS IN SYSTEM ===")
    users = User.objects.all()
    
    if not users:
        print("No users found in the database!")
        return
        
    print(f"Found {users.count()} users in the database.")
    
    for user in users:
        print(f"\nUser: {user.username}")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Is active: {user.is_active}")
        print(f"  Is staff: {user.is_staff}")
        print(f"  Is superuser: {user.is_superuser}")
        print(f"  Last login: {user.last_login}")
        print(f"  Date joined: {user.date_joined}")
        
        # Check if user has userprofile
        has_profile = hasattr(user, 'profile')
        print(f"  Has profile: {has_profile}")
        
        if has_profile:
            print(f"  Student ID: {user.profile.student_id}")

def test_specific_auth(username, password):
    """Test authentication for a specific username and password"""
    print(f"\n=== TESTING AUTHENTICATION FOR USER: {username} ===")
    
    # Check if user exists first
    try:
        user = User.objects.get(username=username)
        print(f"User exists in database: {user.username} (ID: {user.id})")
        print(f"  Is active: {user.is_active}")
        
        # Check password directly
        print(f"Password check: {user.check_password(password)}")
        
    except User.DoesNotExist:
        print(f"User '{username}' does not exist in database!")
        return
        
    # Try authenticating
    authenticated_user = authenticate(username=username, password=password)
    
    if authenticated_user is not None:
        print(f"Authentication successful for {username}!")
    else:
        print(f"Authentication failed for {username}!")
        
        # Print active authentication backends
        from django.contrib.auth import get_backends
        backends = get_backends()
        print("\nActive authentication backends:")
        for backend in backends:
            print(f"  - {backend.__class__.__name__} ({backend.__module__})")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        # Test specific user authentication
        username = sys.argv[1]
        password = sys.argv[2]
        test_specific_auth(username, password)
    else:
        # Test all users
        test_all_users()
        
        # Ask for username and password to test
        print("\nWould you like to test authentication for a specific user?")
        test_user = input("Enter username (or press Enter to skip): ")
        if test_user:
            test_pass = input("Enter password: ")
            test_specific_auth(test_user, test_pass)
