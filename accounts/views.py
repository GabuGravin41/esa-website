from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.contrib.auth import get_backends
from .forms import UserRegistrationForm, UserProfileForm, LoginForm
from core.models import UserProfile
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def login_view(request):
    """Handle user login with both form submission and AJAX"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # LoginForm already handles authentication with the correct backend
            login(request, user)
            
            # Set session expiry if remember me is not checked
            if not form.cleaned_data.get('remember_me', False):
                request.session.set_expiry(0)
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'redirect_url': '/'
                })
            
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')
        else:
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid username or password.'
                })
            
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """Handle user logout"""
    logout(request)
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'redirect_url': '/'
        })
    
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

@ensure_csrf_cookie
def register(request):
    """Handle user registration with both form submission and AJAX"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create the user - UserProfile will be created automatically via signals
            user = form.save()
            
            # Get the first authentication backend (usually ModelBackend)
            backend = get_backends()[0]
            
            # Set the backend attribute on the user
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            
            # Log the user in with the specified backend
            login(request, user)
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'redirect_url': '/'
                })
            
            messages.success(request, f'Account created successfully! Welcome to ESA-KU, {user.username}.')
            return redirect('home')
        else:
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                })
            
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    """Handle user profile view and updates"""
    user = request.user
    
    try:
        # Get the user profile or create one if it doesn't exist
        user_profile = user.profile
    except User.profile.RelatedObjectDoesNotExist:
        # Create a profile if it doesn't exist (shouldn't happen with signals)
        from core.models import UserProfile
        user_profile = UserProfile.objects.create(
            user=user,
            student_id=f"STU{user.id:05d}",
            department="Not specified",
            year_of_study=1
        )
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            # Handle profile update form
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        
        elif 'change_password' in request.POST:
            # Handle password change form
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                
                # Keep the user logged in after password change
                # update_session_auth_hash uses the new password to update the session
                update_session_auth_hash(request, user)
                
                messages.success(request, 'Your password has been updated successfully!')
                return redirect('profile')
            else:
                messages.error(request, 'Please correct the errors below.')
                return render(request, 'accounts/profile.html', {
                    'profile_form': UserProfileForm(instance=user_profile),
                    'password_form': password_form
                })
    
    # Create forms
    profile_form = UserProfileForm(instance=user_profile)
    password_form = PasswordChangeForm(user)
    
    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form
    })

def check_auth_status(request):
    """API endpoint to check user authentication status"""
    if request.user.is_authenticated:
        return JsonResponse({
            'status': 'authenticated',
            'username': request.user.username,
        })
    else:
        return JsonResponse({
            'status': 'unauthenticated'
        })

# Create your views here.
def home(request):
    return render(request, "core/index.html")