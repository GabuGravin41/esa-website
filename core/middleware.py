import logging
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
import json
from django.utils import timezone
from .models import UserProfile
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve, reverse

logger = logging.getLogger(__name__)

class LoginRedirectMiddleware:
    """Middleware to handle login redirects more gracefully."""
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # If we got a 404 response and the URL was accounts/login/
        if response.status_code == 404 and request.path.strip('/') == 'accounts/login':
            # Redirect to the correct login URL
            return redirect('account_login')
            
        # If we got a 403 response (forbidden - usually login required)
        if response.status_code == 403 and not request.user.is_authenticated:
            messages.warning(request, 'You need to be logged in to access this page.')
            return redirect(f"{reverse('account_login')}?next={request.path}")
            
        return response

class ErrorHandlingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Log the error
        logger.error(f"Error: {str(exception)}", exc_info=True, extra={
            'request': request,
            'user': request.user if request.user.is_authenticated else None
        })

        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            error_message = str(exception)
            if isinstance(exception, PermissionDenied):
                status_code = 403
            elif isinstance(exception, ValidationError):
                status_code = 400
            elif isinstance(exception, IntegrityError):
                status_code = 409
            else:
                status_code = 500

            return JsonResponse({
                'error': error_message,
                'status': 'error'
            }, status=status_code)

        # Handle regular requests
        context = {
            'error_message': str(exception),
            'request': request,
            'user': request.user if request.user.is_authenticated else None
        }

        if isinstance(exception, PermissionDenied):
            template = 'core/errors/403.html'
            status_code = 403
        elif isinstance(exception, ValidationError):
            template = 'core/errors/400.html'
            status_code = 400
        elif isinstance(exception, IntegrityError):
            template = 'core/errors/409.html'
            status_code = 409
        else:
            template = 'core/errors/500.html'
            status_code = 500

        html = render_to_string(template, context)
        return JsonResponse({
            'html': html,
            'status': 'error'
        }, status=status_code)

class LoadingStateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request and get the response
        response = self.get_response(request)
        
        # List of paths that should always be rendered as HTML, never as JSON
        excluded_paths = [
            '/resources/', 
            '/events/',
            '/blog/',
            '/membership/',
            '/communities/',
            '/store/',
        ]
        
        # Don't process the response if:
        # 1. It's not a successful response (status code 200)
        # 2. It's not HTML content
        # 3. It's already a JsonResponse
        # 4. The path is in the excluded list
        # 5. It's not an AJAX request (missing X-Requested-With header)
        if (response.status_code != 200 or
            not response.get('Content-Type', '').startswith('text/html') or
            'application/json' in response.get('Content-Type', '') or
            any(request.path.startswith(path) for path in excluded_paths) or
            request.headers.get('X-Requested-With') != 'XMLHttpRequest'):
            return response
        
        # At this point, we know it's an AJAX request expecting HTML
        # that should be wrapped in a JSON response
        from django.http import JsonResponse
        from django.template.loader import render_to_string
        
        try:
            # Create proper JSON response
            content = response.content.decode('utf-8', errors='replace')
            loading_html = render_to_string('core/includes/loading.html')
            
            return JsonResponse({
                'html': content,
                'loading_html': loading_html
            })
        except Exception as e:
            # If anything goes wrong, return the original response
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in LoadingStateMiddleware: {str(e)}")
            return response

class UserActivityMiddleware:
    """
    Middleware that detects admin users and adds admin flags to the request object.
    This enables admin functionality across the site without needing to check in each view.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request - identify if user is an admin
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                
                # Check if the user is a system admin (using Django's is_staff/is_superuser)
                is_system_admin = request.user.is_staff or request.user.is_superuser
                
                # Check if the user has an admin role
                is_role_admin = profile.role and profile.role.is_admin
                
                # Check hardcoded admin users
                is_hardcoded_admin = profile.email in [
                    'admin@example.com',
                    'admin@esa.com',
                    'esaadmin@kenyatta.ac.ke'
                ]
                
                # Combine all admin checks
                request.is_esa_admin = is_system_admin or is_role_admin or is_hardcoded_admin
                
                # Add permission flags to request for easy checking in templates
                request.user_permissions = {
                    'can_manage_events': profile.can_manage_events(),
                    'can_manage_store': profile.can_manage_store(),
                    'can_manage_resources': profile.can_manage_resources(),
                    'can_manage_communities': profile.can_manage_communities(),
                    'can_manage_permissions': profile.can_manage_permissions(),
                }
                
            except Exception:
                # If there's an error (like no profile), default to non-admin
                request.is_esa_admin = False
                request.user_permissions = {}
        else:
            # Not authenticated, definitely not an admin
            request.is_esa_admin = False
            request.user_permissions = {}

        # Continue processing the request
        response = self.get_response(request)
        return response