#!/usr/bin/env python3
import os
import sys

try:
    print("Starting test login script...")
    print(f"Current directory: {os.getcwd()}")
    
    # Set up Django
    print("Setting up Django environment...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'puddle.settings')
    
    import django
    django.setup()
    print("Django setup successful!")
    
    # Import necessary components
    from django.contrib.auth.models import User
    from django.contrib.auth import authenticate, login
    from django.test import RequestFactory, Client
    from core.models import UserProfile
    
    # Test login process
    def test_login_process(username, password):
        """Test the full login process with Django's Client"""
        print(f"\n=== TESTING LOGIN PROCESS FOR: {username} ===")
        
        # First check if user exists
        try:
            user = User.objects.get(username=username)
            print(f"User exists in database: {user.username} (ID: {user.id})")
            print(f"Email: {user.email}")
            print(f"Is active: {user.is_active}")
            
            # Check if user has userprofile
            has_profile = hasattr(user, 'profile')
            print(f"Has profile: {has_profile}")
            
            if has_profile:
                print(f"Student ID: {user.profile.student_id}")
        except User.DoesNotExist:
            print(f"User '{username}' does not exist in database!")
            return
            
        # Test authentication
        authenticated_user = authenticate(username=username, password=password)
        
        if authenticated_user is not None:
            print(f"Authentication successful for {username}!")
            print(f"Auth backend: {authenticated_user.backend}")
        else:
            print(f"Authentication failed for {username}!")
            return
        
        # Test full login with Django Client
        client = Client()
        login_successful = client.login(username=username, password=password)
        
        if login_successful:
            print(f"Client login successful!")
            
            # Test getting a protected page
            response = client.get('/accounts/profile/')
            print(f"Profile page status code: {response.status_code}")
            
            # Test logout
            client.logout()
            print("Client logout successful")
        else:
            print(f"Client login failed!")
    
    if __name__ == "__main__":
        if len(sys.argv) == 3:
            username = sys.argv[1]
            password = sys.argv[2]
            test_login_process(username, password)
        else:
            # Ask for username and password
            username = input("Enter username: ")
            password = input("Enter password: ")
            test_login_process(username, password)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
