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
from threading import current_thread


@ensure_csrf_cookie
def login_view(request):
    """Handle user login with both form submission and AJAX"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # Check if the request is JSON (from the JavaScript API)
        if request.headers.get('Content-Type') == 'application/json':
            import json
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            remember_me = data.get('remember_me', False)
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Set session expiry if remember me is not checked
                if not remember_me:
                    request.session.set_expiry(0)
                
                return JsonResponse({
                    'status': 'success',
                    'redirect_url': '/'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid username or password.'
                })
        
        # Regular form submission
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            # The user is already authenticated by the form's clean() method
            user = form.get_user()
            
            if user is not None:
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
            # The form is not valid (validation errors) - no need to add a message 
            # since form.errors will be displayed in the template
            pass
            
        # Handle AJAX requests for errors
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid username or password.'
            })
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
    """Handle user registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Save student_id to thread for the signal to use
            thread = current_thread()
            thread.student_id = form.cleaned_data.get('student_id')
            
            # Create the user - UserProfile will be created automatically via signals
            user = form.save(commit=True)
            
            # Debug output
            print(f"User created: {user.username} (id: {user.id})")
            print(f"Is user authenticated? {user.is_authenticated}")
            
            # Get the first authentication backend (usually ModelBackend)
            backend = get_backends()[0]
            print(f"Using authentication backend: {backend.__class__.__name__}")
            
            # Set the backend attribute on the user
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            
            # Log the user in with the specified backend
            login(request, user)
            print(f"User logged in? {request.user.is_authenticated}")
            # Send welcome email
            from core.email_service import send_welcome_email_to_user
            send_welcome_email_to_user(user)
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

@ensure_csrf_cookie
def register_with_payment(request):
    """Handle user registration with automatic redirect to payment"""
    if request.user.is_authenticated:
        return redirect('membership')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Save student_id to thread for the signal to use
            thread = current_thread()
            thread.student_id = form.cleaned_data.get('student_id')
            
            # Create the user - UserProfile will be created automatically via signals
            user = form.save(commit=True)
            
            # Log the user in
            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)
            
            # Send welcome email
            from core.email_service import send_welcome_email_to_user
            send_welcome_email_to_user(user)
            
            # TEMPORARY: Redirect to payment coming soon page instead of payment
            # TODO: When M-Pesa credentials are configured, uncomment the original code below and comment out this redirect
            messages.success(request, f'Account created successfully! Welcome to ESA-KU, {user.username}.')
            messages.info(request, 'Payment functionality is coming soon. You can explore the site while we configure the payment system.')
            return redirect('payment_coming_soon')
            
            # ORIGINAL PAYMENT REDIRECT CODE - UNCOMMENT WHEN PAYMENT IS READY:
            # messages.success(request, f'Account created successfully! Welcome to ESA-KU, {user.username}. Please complete your membership payment.')
            # return redirect('membership?show_payment=true&from_registration=true')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register_with_payment.html', {'form': form})

@login_required
def profile(request):
    """Handle user profile view and updates"""
    from core.models import UserProfile
    
    user = request.user
    
    try:
        # Get the user profile or create one if it doesn't exist
        user_profile = user.profile
    except User.profile.RelatedObjectDoesNotExist:
        # Create a profile if it doesn't exist (shouldn't happen with signals)
        user_profile = UserProfile.objects.create(
            user=user,
            student_id=f"STU{user.id:05d}",
            department="Not specified",
            year_of_study=1
        )
    
    if request.method == 'POST':
        # Handle profile update
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        # Update profile fields
        user_profile.phone_number = request.POST.get('phone_number', user_profile.phone_number)
        user_profile.bio = request.POST.get('bio', user_profile.bio)
        user_profile.student_id = request.POST.get('student_id', user_profile.student_id)
        user_profile.department = request.POST.get('department', user_profile.department)
        user_profile.course = request.POST.get('course', user_profile.course)
        
        # Handle year of study
        year_of_study = request.POST.get('year_of_study')
        if year_of_study:
            user_profile.year_of_study = int(year_of_study)
        
        # Handle user type
        user_type = request.POST.get('user_type')
        if user_type:
            user_profile.user_type = user_type
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            user_profile.profile_picture = request.FILES['profile_picture']
        
        user_profile.save()
        messages.success(request, 'Your profile has been updated successfully!')
        return redirect('profile')
    
    # Get choices for template
    year_choices = UserProfile.YEAR_OF_STUDY_CHOICES
    user_type_choices = UserProfile.USER_TYPE_CHOICES
    
    return render(request, 'accounts/new_profile.html', {
        'year_choices': year_choices,
        'user_type_choices': user_type_choices
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