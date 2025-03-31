import logging
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
import json

logger = logging.getLogger(__name__)

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
        # Add loading state to response
        response = self.get_response(request)
        
        # Only add loading state for HTML responses
        if response['Content-Type'].startswith('text/html'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # For AJAX requests, wrap the response in a loading state
                loading_html = render_to_string('core/includes/loading.html')
                if isinstance(response, JsonResponse):
                    data = json.loads(response.content)
                    data['loading_html'] = loading_html
                    response.content = json.dumps(data)
                else:
                    response.content = f'{{"html": "{response.content.decode()}", "loading_html": "{loading_html}"}}'
            else:
                # For regular requests, add loading state to the page
                if hasattr(response, 'content'):
                    content = response.content.decode()
                    loading_html = render_to_string('core/includes/loading.html')
                    response.content = content.replace('</body>', f'{loading_html}</body>')
        
        return response 