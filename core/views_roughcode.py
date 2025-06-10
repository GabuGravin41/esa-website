from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Payment

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

# These are the models you would need to import in the actual views.py file
# from .models import Payment, Membership, ExternalSite, EventRegistration, Order, BlogPost


def site_form(request):
    """Display and process the form for suggesting external engineering sites"""
    from django import forms
    
    class ExternalSiteForm(forms.Form):
        name = forms.CharField(
            max_length=255,
            widget=forms.TextInput(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50'})
        )
        url = forms.URLField(
            widget=forms.URLInput(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50'})
        )
        description = forms.CharField(
            widget=forms.Textarea(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50', 'rows': 4})
        )
        site_type = forms.ChoiceField(
            choices=[
                ('university', 'University Club or Society'),
                ('community', 'Community Resource'),
                ('partner', 'Professional Organization')
            ],
            widget=forms.RadioSelect(attrs={'class': 'mr-2'})
        )
        icon = forms.CharField(
            required=False,
            max_length=50,
            widget=forms.TextInput(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50'})
        )
      
    if request.method == 'POST':
        form = ExternalSiteForm(request.POST)
        if form.is_valid():
            # In the actual implementation, this would call suggest_resource
            # Here we'll just redirect to more_sites with a success message
            messages.success(request, 'Thank you for suggesting this connection! It will be reviewed by an administrator.')
            return redirect('more_sites')
    else:
        form = ExternalSiteForm()
    
    return render(request, 'core/site_form.html', {'form': form})

@login_required
def generate_receipt(request, payment_id):
    """Generate a receipt for a payment"""
    # Get the payment or return 404 if not found
    # In actual implementation, you'd use:
    # payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # For the roughcode, we'll simulate this
    payment = {
        'id': payment_id,
        'amount': 500,
        'currency': 'KES',
        'payment_method': 'mpesa',
        'status': 'completed',
        'transaction_id': f'MPE{payment_id}12345',
        'created_at': timezone.now(),
        'user': request.user
    }
    
    # Get membership if it exists (simulated for roughcode)
    membership = {
        'plan_type': 'other_students',
        'get_plan_type_display': lambda: 'Regular Student',
        'amount': 500,
        'start_date': timezone.now(),
        'end_date': timezone.now() + timezone.timedelta(days=365),
        'status': 'completed'
    }
    
    return render(request, 'core/receipt.html', {
        'payment': payment,
        'membership': membership
    })


@login_required
def payment_history(request):
    """View user's payment history"""
    # In actual implementation, you'd use:
    # payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    # For the roughcode, we'll simulate some payments
    payments = [
        {
            'id': 1,
            'amount': 500,
            'currency': 'KES',
            'payment_method': 'mpesa',
            'get_payment_method_display': lambda: 'M-Pesa',
            'status': 'completed',
            'get_status_display': lambda: 'Completed',
            'transaction_id': 'MPE123456',
            'created_at': timezone.now() - timezone.timedelta(days=30),
            'membership': {
                'get_plan_type_display': lambda: 'Regular Student'
            }
        },
        {
            'id': 2,
            'amount': 300,
            'currency': 'KES',
            'payment_method': 'mpesa',
            'get_payment_method_display': lambda: 'M-Pesa',
            'status': 'failed',
            'get_status_display': lambda: 'Failed',
            'transaction_id': None,
            'created_at': timezone.now() - timezone.timedelta(days=35),
            'membership': {
                'get_plan_type_display': lambda: 'First Year Student'
            }
        },
        {
            'id': 3,
            'amount': 500,
            'currency': 'KES',
            'payment_method': 'paypal',
            'get_payment_method_display': lambda: 'PayPal',
            'status': 'pending',
            'get_status_display': lambda: 'Pending',
            'transaction_id': None,
            'created_at': timezone.now() - timezone.timedelta(days=2),
            'membership': {
                'get_plan_type_display': lambda: 'Regular Student'
            }
        }
    ]
    
    return render(request, 'core/payment_history.html', {
        'payments': payments
    })

@login_required
def dashboard(request):
    """
    User dashboard showing membership status, recent payments, events, and more
    """
    try:
        # In actual implementation, you would use real data from your models
        # For this roughcode, we'll simulate the user profile and related data
        
        # Simulate user profile
        user_profile = {
            'user': request.user,
            'membership_status': 'active',
            'membership_expiry': timezone.now() + timezone.timedelta(days=300),
            'membership_number': 'ESA-KU12345'
        }
        
        # Simulate recent payments (limit to 3)
        recent_payments = [
            {
                'id': 1,
                'amount': 500,
                'currency': 'KES',
                'payment_method': 'mpesa',
                'get_payment_method_display': lambda: 'M-Pesa',
                'status': 'completed',
                'get_status_display': lambda: 'Completed',
                'created_at': timezone.now() - timezone.timedelta(days=30),
                'membership': {
                    'get_plan_type_display': lambda: 'Regular Student'
                }
            },
            {
                'id': 2,
                'amount': 300,
                'currency': 'KES',
                'payment_method': 'mpesa',
                'get_payment_method_display': lambda: 'M-Pesa',
                'status': 'failed',
                'get_status_display': lambda: 'Failed',
                'created_at': timezone.now() - timezone.timedelta(days=35)
            }
        ]
        
        # Simulate upcoming events
        upcoming_events = [
            {
                'event': {
                    'id': 1,
                    'title': 'Engineering Workshop',
                    'start_date': timezone.now() + timezone.timedelta(days=15),
                    'location': 'Engineering Block'
                }
            }
        ]
        
        # Simulate recent orders
        recent_orders = [
            {
                'id': 1,
                'created_at': timezone.now() - timezone.timedelta(days=10),
                'total_amount': 250
            }
        ]
        
        # Simulate recent posts
        recent_posts = [
            {
                'id': 1,
                'title': 'Engineering Ethics',
                'created_at': timezone.now() - timezone.timedelta(days=5)
            }
        ]
        
        return render(request, 'core/dashboard.html', {
            'user_profile': user_profile,
            'membership_status': user_profile['membership_status'],
            'membership_expiry': user_profile['membership_expiry'],
            'recent_payments': recent_payments,
            'upcoming_events': upcoming_events,
            'recent_orders': recent_orders,
            'recent_posts': recent_posts,
        })
        
    except Exception as e:
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return redirect('profile')