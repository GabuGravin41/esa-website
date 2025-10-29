from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.db import IntegrityError, models
from django.db.models import Count, Q, Prefetch, F
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
import datetime
import json
import uuid
import os
import re
import random
from decimal import Decimal
from django.conf import settings
import requests
import logging
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.core.mail import send_mail
from .email_service import send_payment_confirmation_email
from dateutil.relativedelta import relativedelta

from .models import (
    Event, EventRegistration, ExternalSite, Product, Order,
    OrderItem, BlogPost, Comment, Resource,
    MembershipPlan, Membership, UserProfile,
    Payment, MpesaTransaction, Community,
    Cart, CartItem, UserRole, CommunityMember,
    Discussion, EventAttendee, ResourceTag, Announcement, NewsletterSubscriber, Partner
)
from .forms import (
    EventForm, EventRegistrationForm,
    ProductForm, OrderForm, OrderItemForm,
    BlogPostForm, CommentForm, ResourceForm,
    MembershipPaymentForm, MpesaPaymentForm,
    ContactForm, CommunityForm, CommunityEditForm, DiscussionForm,
    MemberGetMemberForm
)
from .services import MpesaService, PayPalService

logger = logging.getLogger(__name__)

def home(request):
    # Handle newsletter subscription form submission
    if request.method == 'POST' and request.POST.get('form_type') == 'newsletter':
        email = request.POST.get('email')
        if email:
            try:
                NewsletterSubscriber.objects.create(email=email)
                messages.success(request, 'Thank you for subscribing to our newsletter!')
            except IntegrityError:
                messages.info(request, 'You are already subscribed to our newsletter.')
            except Exception as e:
                messages.error(request, 'An error occurred while processing your subscription. Please try again.')
        else:
            messages.error(request, 'Please provide a valid email address.')

    # Cache key for home page data
    cache_key = 'home_page_data'
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        # Get featured or upcoming events (limited to 3) with optimized queries
        current_date = timezone.now().date()
        
        # Optimized query with select_related for foreign keys
        featured_events = Event.objects.select_related('created_by', 'community').filter(
            is_active=True, 
            featured=True, 
            end_date__gte=current_date
        ).order_by('start_date')[:3]
        
        # If we don't have enough featured events, get regular upcoming events
        if featured_events.count() < 3:
            regular_events = Event.objects.select_related('created_by', 'community').filter(
                is_active=True,
                end_date__gte=current_date,
            ).exclude(id__in=featured_events.values_list('id', flat=True)).order_by('start_date')[:3]
            events = list(featured_events) + list(regular_events)[:3-len(featured_events)]
        else:
            events = list(featured_events)
        
        # Get blog posts with author info (optimized)
        blog_posts = BlogPost.objects.select_related('author__user').filter(
            is_published=True
        ).order_by('-created_at')[:2]
        
        # Fetch active announcements that are not expired
        announcements = Announcement.objects.filter(
            is_active=True
        ).exclude(expiry_date__lt=timezone.now())[:5]
        
        # Get the next major event for the countdown timer
        next_major_event = Event.objects.select_related('created_by').filter(
            is_active=True, 
            featured=True,
            end_date__gte=current_date
        ).order_by('start_date').first()
        
        # If no featured event found, get the nearest upcoming event
        if not next_major_event:
            next_major_event = Event.objects.select_related('created_by').filter(
                is_active=True,
                end_date__gte=current_date
            ).order_by('start_date').first()
        
        # Cache the data for 5 minutes
        cached_data = {
            'events': events,
            'blog_posts': blog_posts,
            'announcements': announcements,
            'next_major_event': next_major_event,
        }
        cache.set(cache_key, cached_data, 300)  # 5 minutes
    
    # Extract cached data
    events = cached_data['events']
    blog_posts = cached_data['blog_posts']
    announcements = cached_data['announcements']
    next_major_event = cached_data['next_major_event']
    
    # Fetch active partners
    partners = Partner.objects.filter(is_active=True)

    context = {
        'events': events,
        'blog_posts': blog_posts,
        'announcements': announcements,
        'next_major_event': next_major_event,
        'partners': partners,
    }
    return render(request, 'core/home.html', context)

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    from .email_service import EmailService
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            # Send email to admin (ensure correct recipient)
            EmailService.send_email(
                subject=f"Contact Form: {contact.subject}",
                recipient_list=[settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else 'esa.kenyattauniv@gmail.com'],
                template_name="core/emails/contact_message.html",
                context={
                    'name': contact.name,
                    'email': contact.email,
                    'subject': contact.subject,
                    'message': contact.message,
                },
            )
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'core/contact.html', {'form': form})

def membership(request):
    is_member = False
    if request.user.is_authenticated:
        is_member = Membership.objects.filter(user=request.user, is_active=True).exists()
    
    plans = MembershipPlan.objects.all()
    return render(request, 'core/membership.html', {
        'is_member': is_member,
        'plans': plans
    })

@login_required
def join_membership(request, plan_id):
    """Handle membership subscription for a specific plan"""
    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, 'Please complete your profile first.')
        return redirect('profile')
    
    # Check if user is already a member with active membership
    if profile.is_membership_active():
        messages.info(request, 'You already have an active membership.')
        return redirect('membership')
    
    if request.method == 'POST':
        form = MembershipPaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            
            # Calculate membership dates
            start_date = timezone.now()
            end_date = start_date + datetime.timedelta(days=plan.duration * 30)  # Approximate months
            
            # Create pending membership
            membership = Membership.objects.create(
                user=profile,
                plan=plan,
                start_date=start_date,
                end_date=end_date,
                status='pending',
                payment_status=False
            )
            
            # Create payment record
            payment = Payment.objects.create(
                user=request.user,
                membership=membership,
                amount=plan.price,
                currency='KES',
                payment_method=payment_method,
                status='pending'
            )
            
            # Handle payment based on method
            if payment_method == 'mpesa':
                return redirect('mpesa_payment', payment_id=payment.id)
            elif payment_method == 'paypal':
                return redirect('paypal_payment', payment_id=payment.id)
    else:
        form = MembershipPaymentForm()
    
    return render(request, 'core/join_membership.html', {
        'plan': plan,
        'form': form
    })

@login_required
def mpesa_payment(request, payment_id):
    """Handle M-Pesa payment for membership"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user, status='pending')
    
    if payment.payment_method != 'mpesa':
        messages.error(request, 'Invalid payment method')
        return redirect('membership')
    
    if request.method == 'POST':
        form = MpesaPaymentForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            amount = payment.amount
            
            # Create reference for the transaction
            reference = f"ESA-{payment.id}"
            
            # Get plan name from membership if available
            try:
                membership = payment.membership
                if hasattr(membership, 'plan') and membership.plan:
                    plan_name = membership.plan.name
                elif hasattr(membership, 'plan_type'):
                    plan_name = membership.get_plan_type_display()
                else:
                    plan_name = "Membership"
            except:
                plan_name = "Membership"
            
            description = f"ESA-KU Membership Payment: {plan_name}"
            
            # Create M-Pesa transaction record
            mpesa_tx = MpesaTransaction.objects.create(
                payment=payment,
                phone_number=phone_number,
                amount=amount,
                status='pending'
            )
            
            # Initiate M-Pesa STK push
            mpesa_service = MpesaService()
            response = mpesa_service.initiate_stk_push(
                phone_number=phone_number,
                amount=int(amount),
                reference=reference,
                description=description
            )
            
            # Handle the response
            if 'CheckoutRequestID' in response:
                # Store checkout request ID for later verification
                mpesa_tx.checkout_request_id = response['CheckoutRequestID']
                mpesa_tx.save(update_fields=['checkout_request_id'])
                
                messages.success(request, 'Payment initiated. Please check your phone to complete the transaction.')
                return redirect('payment_status', payment_id=payment.id)
            else:
                messages.error(request, f"Failed to initiate payment: {json.dumps(response)}")
    else:
        form = MpesaPaymentForm(initial={'amount': payment.amount})
    
    return render(request, 'core/mpesa_payment.html', {
        'payment': payment,
        'membership': getattr(payment, 'membership', None),
        'form': form
    })

@login_required
def paypal_payment(request, payment_id):
    """Handle PayPal payment for membership"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user, status='pending')
    
    if payment.payment_method != 'paypal':
        messages.error(request, 'Invalid payment method')
        return redirect('membership')
    
    # Create PayPal order
    paypal_service = PayPalService()
    
    # Convert KES to USD for PayPal (simplified conversion - in production use a real exchange rate)
    amount_usd = round(float(payment.amount) / 130, 2)  # Approximate KES to USD conversion
    
    return_url = request.build_absolute_uri(reverse('paypal_success', kwargs={'payment_id': payment.id}))
    cancel_url = request.build_absolute_uri(reverse('paypal_cancel', kwargs={'payment_id': payment.id}))
    
    response = paypal_service.create_order(
        amount=amount_usd,
        currency='USD',
        reference=f"ESA-{payment.id}",
        return_url=return_url,
        cancel_url=cancel_url
    )
    
    # Store payment token for later verification
    if 'id' in response:
        payment.payment_token = response['id']
        payment.save(update_fields=['payment_token'])
        
        # Find the approval URL
        for link in response['links']:
            if link['rel'] == 'approve':
                return redirect(link['href'])
    
    messages.error(request, f"Failed to initiate PayPal payment: {json.dumps(response)}")
    return redirect('join_membership', plan_id=payment.membership.plan.id)

@login_required
def paypal_success(request, payment_id):
    """Handle successful PayPal payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Get the order ID from the URL
    order_id = request.GET.get('token')
    
    if order_id and order_id == payment.payment_token:
        # Capture the payment
        paypal_service = PayPalService()
        response = paypal_service.capture_order(order_id)
        
        if 'status' in response and response['status'] == 'COMPLETED':
            # Update payment and membership
            payment.status = 'completed'
            payment.transaction_id = order_id
            payment.save(update_fields=['status', 'transaction_id'])
            
            # Activate membership
            payment.complete_payment(order_id)
            
            messages.success(request, 'Payment completed successfully! Your membership is now active.')
            return redirect('dashboard')
    
    messages.error(request, 'Failed to complete payment. Please try again or contact support.')
    return redirect('membership')

@login_required
def paypal_cancel(request, payment_id):
    """Handle cancelled PayPal payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Update payment status
    payment.status = 'cancelled'
    payment.save(update_fields=['status'])
    
    # Update membership status if it exists
    if payment.membership:
        membership = payment.membership
        membership.status = 'cancelled'
        membership.is_active = False
        membership.save()
        
        # Update user profile if needed
        try:
            profile = payment.user.profile
            if profile.membership_status == 'active' and profile.membership_expiry:
                # Only update if this was the active membership
                if profile.membership_expiry == membership.end_date.date():
                    profile.membership_status = 'inactive'
                    profile.membership_expiry = None
                    profile.save()
        except UserProfile.DoesNotExist:
            pass
    
    messages.info(request, 'Payment was cancelled. Your membership has not been activated.')
    return redirect('membership')

@login_required
def payment_status(request, payment_id):
    """Check payment status"""
    # For member-get-member payments, the payment user might be different from request user
    # So we need to check if the current user is either the payment user or the referrer
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Check if user has permission to view this payment
    has_permission = False
    if payment.user == request.user:
        has_permission = True
    else:
        # Check if this is a member-get-member payment and current user is the referrer
        try:
            membership = Membership.objects.get(payment=payment)
            if membership.referred_by == request.user:
                has_permission = True
        except Membership.DoesNotExist:
            pass
    
    if not has_permission:
        messages.error(request, 'You do not have permission to view this payment.')
        return redirect('dashboard')
    
    # Check for M-Pesa transaction
    if payment.payment_method == 'mpesa' and hasattr(payment, 'mpesa_transaction'):
        mpesa_tx = payment.mpesa_transaction
        
        # Only query status if we have a checkout request ID and status is still pending
        if mpesa_tx.checkout_request_id and mpesa_tx.status == 'pending' and payment.status == 'pending':
            mpesa_service = MpesaService()
            response = mpesa_service.query_transaction_status(mpesa_tx.checkout_request_id)
            
            # Process response if successful
            if 'ResultCode' in response and response['ResultCode'] == '0':
                # Update transaction details
                mpesa_tx.status = 'completed'
                mpesa_tx.mpesa_receipt = response.get('MpesaReceiptNumber')
                mpesa_tx.save(update_fields=['status', 'mpesa_receipt'])
                
                # Complete payment and activate membership
                payment.complete_payment(mpesa_tx.mpesa_receipt)
                
                messages.success(request, 'Payment completed successfully! Your membership is now active.')
                return redirect('dashboard')
    
    # Check if this is a membership payment or a regular order payment
    membership = None
    order = None
    
    # Try to get membership associated with this payment
    try:
        membership = Membership.objects.get(payment=payment)
    except Membership.DoesNotExist:
        # Try to get order associated with this payment
        try:
            order = Order.objects.get(payment=payment)
        except Order.DoesNotExist:
            pass
    
    return render(request, 'core/payment_status.html', {
        'payment': payment,
        'membership': membership,
        'order': order,
        'DEBUG': settings.DEBUG
    })

@require_POST
@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa callback from Safaricom for both membership and store payments"""
    logging.info("Received M-Pesa callback")
    
    try:
        # Parse the callback JSON
        data = json.loads(request.body)
        logging.info(f"M-Pesa callback data: {json.dumps(data)}")
        
        body = data.get('Body', {})
        callback_data = body.get('stkCallback', {})
        
        # Extract important details
        checkout_request_id = callback_data.get('CheckoutRequestID')
        result_code = callback_data.get('ResultCode')
        result_desc = callback_data.get('ResultDesc')
        
        logging.info(f"M-Pesa callback processing: Request ID: {checkout_request_id}, Result: {result_code} - {result_desc}")
        
        # Find the transaction
        try:
            mpesa_tx = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
            
            if result_code == 0:  # Success
                # Extract transaction details
                items = callback_data.get('CallbackMetadata', {}).get('Item', [])
                receipt_number = next((item['Value'] for item in items if item['Name'] == 'MpesaReceiptNumber'), None)
                transaction_date = next((item['Value'] for item in items if item['Name'] == 'TransactionDate'), None)
                
                if transaction_date:
                    # Convert to proper datetime
                    transaction_date = datetime.strptime(str(transaction_date), '%Y%m%d%H%M%S')
                else:
                    transaction_date = timezone.now()
                
                # Update transaction
                mpesa_tx.status = 'completed'
                mpesa_tx.mpesa_receipt = receipt_number
                mpesa_tx.transaction_date = transaction_date
                mpesa_tx.result_code = str(result_code)
                mpesa_tx.result_description = result_desc
                mpesa_tx.save()
                
                # Complete payment
                payment = mpesa_tx.payment
                payment.complete_payment(receipt_number)
                
                # If this is an order payment, update the order status
                if hasattr(payment, 'order'):
                    order = payment.order
                    order.status = 'completed'
                    order.payment_status = True
                    order.save()
                    
                    # Send confirmation email
                    try:
                        from core.email_service import send_order_confirmation_email
                        send_order_confirmation_email(order.user, order)
                    except Exception as e:
                        logging.error(f"Failed to send order confirmation email: {str(e)}")
            else:
                # Payment failed
                mpesa_tx.status = 'failed'
                mpesa_tx.result_code = str(result_code)
                mpesa_tx.result_description = result_desc
                mpesa_tx.save()
                
                # Mark payment as failed
                payment = mpesa_tx.payment
                payment.status = 'failed'
                payment.notes = f"Failed: {result_desc}"
                payment.save()
            
            return JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Callback processed successfully"
            })
        except MpesaTransaction.DoesNotExist:
            logging.error(f"M-Pesa transaction not found for checkout request ID: {checkout_request_id}")
            return JsonResponse({
                "ResultCode": 1,
                "ResultDesc": "Transaction not found"
            })
    except Exception as e:
        logging.exception(f"Error processing M-Pesa callback: {str(e)}")
        return JsonResponse({
            "ResultCode": 1,
            "ResultDesc": f"Error processing callback: {str(e)}"
        })
        
    
@login_required
def events(request):
    """Display all events"""
    # Get all future events
    current_time = timezone.now()
    current_date = current_time.date()  # Convert to date for proper comparison
    future_events = Event.objects.filter(end_date__gt=current_date).order_by('start_date')
    
    # Get past events (optional to show)
    past_events = Event.objects.filter(end_date__lte=current_date).order_by('-start_date')[:5]  # Limit to recent past events
    
    # Filter by event type if specified
    event_type = request.GET.get('type')
    if event_type:
        future_events = future_events.filter(event_type=event_type)
    
    # Date filtering
    date_filter = request.GET.get('date')
    if date_filter:
        today = timezone.now().date()
        if date_filter == 'today':
            future_events = future_events.filter(start_date__date=today)
        elif date_filter == 'week':
            end_of_week = today + datetime.timedelta(days=7)
            future_events = future_events.filter(start_date__date__range=[today, end_of_week])
        elif date_filter == 'month':
            end_of_month = today.replace(day=28) + datetime.timedelta(days=4)  # This will give us the end of month
            end_of_month = end_of_month - datetime.timedelta(days=end_of_month.day)
            future_events = future_events.filter(start_date__date__range=[today, end_of_month])
        elif date_filter == 'next_month':
            start_of_next_month = today.replace(day=1) + datetime.timedelta(days=32)  # Move to next month
            start_of_next_month = start_of_next_month.replace(day=1)
            end_of_next_month = start_of_next_month.replace(day=28) + datetime.timedelta(days=4)  # This will give us the end of month
            end_of_next_month = end_of_next_month - datetime.timedelta(days=end_of_next_month.day)
            future_events = future_events.filter(start_date__date__range=[start_of_next_month, end_of_next_month])
    
    # Filter by location
    location_filter = request.GET.get('location')
    if location_filter:
        if location_filter == 'Virtual':
            future_events = future_events.filter(Q(location__iexact='Online') | Q(location__iexact='Virtual') | Q(online_link__isnull=False))
        else:
            future_events = future_events.filter(location__icontains=location_filter)
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        future_events = future_events.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Check which events the user is registered for
    user_registrations = []
    if request.user.is_authenticated:
        try:
            # Get the user profile if it exists
            # This handles both admin and regular users
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                user_registrations = EventRegistration.objects.filter(user=user_profile).values_list('event_id', flat=True)
            except UserProfile.DoesNotExist:
                # If user doesn't have a profile (might be an admin user without profile)
                # Leave user_registrations as empty list
                pass
        except Exception as e:
            # Log the error but continue without registrations
            logger.error(f"Error getting user registrations: {str(e)}")

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(future_events, 9)  # Show 9 events per page
    
    try:
        paginated_events = paginator.page(page)
    except:
        paginated_events = paginator.page(1)
    
    return render(request, 'core/events.html', {
        'future_events': paginated_events,
        'past_events': past_events,
        'user_registrations': user_registrations,
        'event_type': event_type,
        'date_filter': date_filter,
        'location_filter': location_filter,
        'search_query': search_query,
        'title': 'Events',
        'current_month': current_date.month,
        'current_year': current_date.year
    })

@login_required
def event_detail(request, event_id):
    """Display details for a specific event"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is registered
    registration = None
    is_registered = False
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            try:
                registration = EventRegistration.objects.get(event=event, user=user_profile)
                is_registered = True
            except EventRegistration.DoesNotExist:
                is_registered = False
        except UserProfile.DoesNotExist:
            is_registered = False
    
    # Get attendees count
    attendees_count = EventRegistration.objects.filter(event=event).count()
    
    # Get similar events
    current_date = timezone.now().date()  # Convert to date for proper comparison
    similar_events = Event.objects.filter(
        event_type=event.event_type, 
        end_date__gt=current_date
    ).exclude(id=event.id).order_by('start_date')[:3]
    
    # Check if user can edit the event
    can_edit = False
    if hasattr(request.user, 'profile'):
        try:
            profile = request.user.profile
            can_edit = profile.can_manage_events() or (event.created_by == request.user)
        except UserProfile.DoesNotExist:
            can_edit = False
    
    return render(request, 'core/event_detail.html', {
        'event': event,
        'is_registered': is_registered,
        'registration': registration,
        'attendees_count': attendees_count,
        'similar_events': similar_events,
        'title': event.title,
        'can_edit': can_edit,
    })

@login_required
def event_create(request):
    """Create a new event"""
    # Check if user has permission to create events
    if not request.user.is_authenticated or not hasattr(request.user, 'profile') or not request.user.profile.can_manage_events():
        messages.error(request, "You don't have permission to create events.")
        return redirect('events')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            
            messages.success(request, 'Event created successfully!')
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    
    return render(request, 'core/event_form.html', {
        'form': form,
        'title': 'Create Event',
        'is_create': True
    })

@login_required
def event_edit(request, event_id):
    """Edit an existing event"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user has permission to edit this event
    can_edit = False
    if hasattr(request.user, 'profile'):
        try:
            profile = request.user.profile
            can_edit = profile.can_manage_events() or (event.created_by == request.user)
        except UserProfile.DoesNotExist:
            can_edit = False
            
    if not can_edit:
        messages.error(request, "You don't have permission to edit this event.")
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'core/event_form.html', {
        'form': form,
        'event': event,
        'title': 'Edit Event',
        'is_create': False
    })

@login_required
def event_delete(request, event_id):
    """Delete an event"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user has permission to delete this event
    can_delete = False
    if hasattr(request.user, 'profile'):
        try:
            profile = request.user.profile
            can_delete = profile.can_manage_events() or (event.created_by == request.user)
        except UserProfile.DoesNotExist:
            can_delete = False
    
    if not can_delete:
        messages.error(request, "You don't have permission to delete this event.")
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        # Delete registrations first (to avoid foreign key constraints)
        EventRegistration.objects.filter(event=event).delete()
        
        # Delete attendees if any (for community events)
        EventAttendee.objects.filter(event=event).delete()
        
        # Delete event image if it exists
        if event.image:
            if os.path.exists(event.image.path):
                os.remove(event.image.path)
        
        event.delete()
        messages.success(request, 'Event deleted successfully!')
        return redirect('events')
    
    return render(request, 'core/event_confirm_delete.html', {
        'event': event,
        'title': 'Delete Event'
    })

@login_required
def event_register(request, event_id):
    """Register user for an event"""
    event = get_object_or_404(Event, id=event_id)
    
    # Get user profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found. Please complete your profile setup first.")
        return redirect('event_detail', event_id=event.id)
    
    # Check if event is in the past
    current_date = timezone.now().date()  # Convert datetime to date for comparison
    if event.end_date < current_date:
        messages.error(request, "You cannot register for past events.")
        return redirect('event_detail', event_id=event.id)
    
    # Check if user is already registered
    if EventRegistration.objects.filter(event=event, user=user_profile).exists():
        messages.info(request, "You are already registered for this event.")
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        form = EventRegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.event = event
            registration.user = user_profile  # Use user_profile instead of request.user
            registration.save()
            
            
            # Send confirmation email
            try:
                from .email_service import send_event_registration_email
                send_event_registration_email(request.user, event, registration)
            except Exception as e:
                # Log the error but don't stop the registration
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send registration confirmation email: {str(e)}")
            
            messages.success(request, "You have successfully registered for this event!")
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventRegistrationForm()
    
    return render(request, 'core/event_registration_form.html', {
        'form': form,
        'event': event,
        'title': 'Register for Event'
    })

@login_required
def event_cancel_registration(request, event_id):
    """Cancel event registration"""
    event = get_object_or_404(Event, id=event_id)
    
    # Get user profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found. Please complete your profile setup first.")
        return redirect('event_detail', event_id=event.id)
    
    # Check if event already started
    current_date = timezone.now().date()  # Convert datetime to date for comparison
    if event.start_date <= current_date:
        messages.error(request, "You cannot cancel registration for an event that has already started.")
        return redirect('event_detail', event_id=event.id)
    
    # Check if registration exists
    registration = get_object_or_404(EventRegistration, event=event, user=user_profile)
    
    if request.method == 'POST':
        registration.delete()
        messages.success(request, "Your registration has been canceled.")
        return redirect('events')
    
    return render(request, 'core/event_cancel_registration.html', {
        'event': event,
        'title': 'Cancel Registration'
    })

def blog(request):
    # Get filter parameters from URL
    category = request.GET.get('category')
    sort = request.GET.get('sort', 'latest')
    search = request.GET.get('search')
    year = request.GET.get('year')  # Add year parameter for journal archives
    
    try:
        # Base queryset - only published posts
        posts = BlogPost.objects.filter(is_published=True)
        
        # Apply category filter
        if category:
            posts = posts.filter(category=category)
        
        # Apply search filter
        if search:
            posts = posts.filter(
                models.Q(title__icontains=search) | 
                models.Q(content__icontains=search)
            )
            
        # Apply year filter (for journal archives)
        if year:
            posts = posts.filter(created_at__year=year)
        
        # Apply sorting
        if sort == 'latest':
            posts = posts.order_by('-created_at')
        elif sort == 'popular':
            # Placeholder for popular sorting - would normally count views or interactions
            # For now, just randomize as an example
            posts = posts.order_by('?')
        elif sort == 'trending':
            # Placeholder for trending - would normally be based on recent
            # For now, just use recent posts as an example
            posts = posts.order_by('-created_at')
    except Exception as e:
        # If there's a database error, log it and return an empty queryset
        print(f"Database error: {e}")
        posts = BlogPost.objects.none()
    
    # Get recent posts for sidebar
    try:
        recent_posts = BlogPost.objects.filter(is_published=True).order_by('-created_at')[:5]
    except Exception as e:
        print(f"Error getting recent posts: {e}")
        recent_posts = []
    
    # Get all categories for the sidebar filter
    categories = [choice[0] for choice in BlogPost.CATEGORY_CHOICES]
    
    # Count posts per category
    category_counts = {}
    for cat in categories:
        category_counts[cat] = BlogPost.objects.filter(category=cat, is_published=True).count()
    
    # Check if we have academic categories in results to highlight the section
    has_academic = posts.filter(
        models.Q(category='research') | 
        models.Q(category='thesis')
    ).exists()
    
    context = {
        'posts': posts,
        'recent_posts': recent_posts,
        'category': category,
        'sort': sort,
        'search': search,
        'year': year,  # Add year to context
        'categories': categories,
        'category_counts': category_counts,
        'has_academic': has_academic,  # Flag for academic content
    }
    return render(request, 'core/blog.html', context)

def blog_post_detail(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    comments = post.comments.all().order_by('-created_at')
    
    # Get recent posts for "You might also like" section
    recent_posts = BlogPost.objects.filter(is_published=True).exclude(id=post_id).order_by('-created_at')[:4]

    # Same category posts
    same_category_posts = BlogPost.objects.filter(
        category=post.category, 
        is_published=True
    ).exclude(id=post_id).order_by('-created_at')[:3]

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            # Get or create a default user for comments when not authenticated
            # In a real implementation, this would use the authenticated user
            default_user, created = User.objects.get_or_create(
                username='default_commenter',
                defaults={'email': 'commenter@example.com'}
            )
            # Get or create a default profile for the user
            default_profile, created = UserProfile.objects.get_or_create(
                user=default_user,
                defaults={
                    'student_id': 'COMMENT001',
                    'department': 'Comment Department',
                    'year_of_study': 1,
                    'bio': 'Default commenter profile',
                    'phone_number': ''
                }
            )
            
            # Save the comment
            comment = form.save(commit=False)
            comment.author = default_profile
            comment.post = post
            comment.save()
            
            messages.success(request, 'Comment added successfully!')
            return redirect('blog_post_detail', post_id=post.id)
    else:
        form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'recent_posts': recent_posts,
        'same_category_posts': same_category_posts,
    }
    
    # Add permission flags for template
    can_edit = False
    if request.user.is_authenticated:
        try:
            if hasattr(request.user, 'profile'):
                can_edit = request.user.profile.is_esa_admin() or post.author == request.user.profile
        except:
            pass
    context['can_edit'] = can_edit
    
    return render(request, 'core/blog_post_detail.html', context)

@login_required
def resources(request):
    """Display all approved resources"""
    resource_list = Resource.objects.filter(is_approved=True)
    
    # Filter by category if specified
    category = request.GET.get('category')
    if category:
        resource_list = resource_list.filter(category=category)
    
    # Filter by tag if specified
    tag = request.GET.get('tag')
    if tag:
        resource_list = resource_list.filter(tags__slug=tag)
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        resource_list = resource_list.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    # Sort functionality
    sort = request.GET.get('sort', 'latest')
    if sort == 'popular':
        resource_list = resource_list.order_by('-download_count')
    elif sort == 'views':
        resource_list = resource_list.order_by('-view_count')
    else:  # default to latest
        resource_list = resource_list.order_by('-created_at')

    # Categories for filtering sidebar
    categories = dict(Resource.CATEGORY_CHOICES)
    
    # Get counts for each category
    document_count = Resource.objects.filter(is_approved=True, category='document').count()
    video_count = Resource.objects.filter(is_approved=True, category='video').count()
    link_count = Resource.objects.filter(is_approved=True, category='link').count()
    
    # Get popular tags
    tags = ResourceTag.objects.annotate(
        resource_count=Count('resource')
    ).filter(resource_count__gt=0).order_by('-resource_count')[:10]
    
    # Featured resources
    featured_resources = Resource.objects.filter(is_approved=True, is_featured=True)[:5]
    
    # Check if user is admin for pending resources notification
    is_admin = False
    pending_resources_count = 0
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            is_admin = profile.is_esa_admin()
            if is_admin:
                pending_resources_count = Resource.objects.filter(is_approved=False).count()
        except:
            pass
    
    # Get popular resources for sidebar
    popular_resources = Resource.objects.filter(is_approved=True).order_by('-download_count')[:5]
    
    return render(request, 'core/resources.html', {
        'resources': resource_list,
        'categories': categories,
        'tags': tags,
        'featured_resources': featured_resources,
        'category': category,
        'tag': tag,
        'search_query': search_query,
        'sort': sort,
        'title': 'Resources Library',
        'document_count': document_count,
        'video_count': video_count,
        'link_count': link_count,
        'is_admin': is_admin,
        'pending_resources_count': pending_resources_count,
        'popular_resources': popular_resources
    })

@login_required
def resource_create(request):
    """Create a new resource"""
    # All authenticated users can create resources
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.uploaded_by = request.user.profile
            
            # Automatically approve resources uploaded by admins
            if request.user.profile.is_esa_admin():
                resource.is_approved = True
            
            resource.save()
            
            # Handle tags
            form.save_m2m()  # Save tags
            
            messages.success(request, 'Resource added successfully! It will be reviewed by an administrator.')
            return redirect('resource_detail', resource_id=resource.id)
    else:
        form = ResourceForm()
    
    return render(request, 'core/resource_form.html', {
        'form': form,
        'title': 'Upload Resource',
        'is_create': True
    })

@login_required
def resource_detail(request, resource_id):
    """Display resource details"""
    resource = get_object_or_404(Resource, id=resource_id)
    
    # Check if user can view non-approved resources
    can_view = resource.is_approved
    if not can_view:
        try:
            # Check if user is admin or resource owner
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                can_view = profile.is_esa_admin() or (resource.uploaded_by and resource.uploaded_by.user == request.user)
        except UserProfile.DoesNotExist:
            can_view = False
    
    if not can_view:
        messages.error(request, "This resource has not been approved yet.")
        return redirect('resources')
    
    # Increment view count
    if request.session.get(f'viewed_resource_{resource_id}') != 'yes':
        resource.increment_view_count()
        request.session[f'viewed_resource_{resource_id}'] = 'yes'
    
    # Get related resources by tag
    related_resources = Resource.objects.filter(
        is_approved=True, 
        tags__in=resource.tags.all()
    ).exclude(id=resource.id).distinct()[:4]
    
    # If we don't have enough related resources by tag, add some from the same category
    if related_resources.count() < 4:
        more_resources = Resource.objects.filter(
            is_approved=True,
            category=resource.category
        ).exclude(
            id__in=[r.id for r in [resource] + list(related_resources)]
        )[:4-related_resources.count()]
        
        # Combine the querysets
        related_resources = list(related_resources) + list(more_resources)
    
    # Check if user can edit
    can_edit = False
    try:
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            can_edit = profile.is_esa_admin() or (resource.uploaded_by and resource.uploaded_by.user == request.user)
    except UserProfile.DoesNotExist:
        can_edit = False
    
    return render(request, 'core/resource_detail.html', {
        'resource': resource,
        'related_resources': related_resources,
        'title': resource.title,
        'can_edit': can_edit
    })

@login_required
def resource_edit(request, resource_id):
    """Edit an existing resource"""
    resource = get_object_or_404(Resource, id=resource_id)
    
    # Check if user has permission to edit this resource
    if not (request.user.profile.is_esa_admin() or (resource.uploaded_by and resource.uploaded_by.user == request.user)):
        messages.error(request, "You don't have permission to edit this resource.")
        return redirect('resource_detail', resource_id=resource.id)
    
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            # If a regular user edits, set approved to False for re-review
            if not request.user.profile.is_esa_admin() and resource.uploaded_by and resource.uploaded_by.user == request.user:
                resource = form.save(commit=False)
                resource.is_approved = False
                resource.save()
                form.save_m2m()  # Save tags
                messages.success(request, 'Resource updated successfully! It will be reviewed by an administrator.')
            else:
                form.save()
                messages.success(request, 'Resource updated successfully!')
            
            return redirect('resource_detail', resource_id=resource.id)
    else:
        form = ResourceForm(instance=resource)
    
    return render(request, 'core/resource_form.html', {
        'form': form,
        'resource': resource,
        'title': 'Edit Resource',
        'is_create': False
    })

@login_required
def resource_delete(request, resource_id):
    """Delete a resource"""
    resource = get_object_or_404(Resource, id=resource_id)
    
    # Check if user has permission to delete this resource
    if not (request.user.profile.is_esa_admin() or (resource.uploaded_by and resource.uploaded_by.user == request.user)):
        messages.error(request, "You don't have permission to delete this resource.")
        return redirect('resource_detail', resource_id=resource.id)
    
    if request.method == 'POST':
        # Delete associated files
        if resource.file:
            if os.path.exists(resource.file.path):
                os.remove(resource.file.path)
        
        if resource.thumbnail:
            if os.path.exists(resource.thumbnail.path):
                os.remove(resource.thumbnail.path)
        
        resource.delete()
        messages.success(request, 'Resource deleted successfully!')
        return redirect('resources')
    
    return render(request, 'core/resource_confirm_delete.html', {
        'resource': resource,
        'title': 'Delete Resource'
    })

@login_required
def resource_download(request, resource_id):
    """Download a resource file"""
    resource = get_object_or_404(Resource, id=resource_id)
    
    # If it's a link type resource, redirect to the link
    if resource.category == 'link' and resource.link:
        # Increment download count
        resource.increment_download_count()
        return redirect(resource.link)
    
    # Check if resource has a file
    if not resource.file:
        messages.error(request, "This resource doesn't have a downloadable file.")
        return redirect('resource_detail', resource_id=resource.id)
    
    # Check if user can download non-approved resources
    if not resource.is_approved and not request.user.profile.is_esa_admin() and resource.uploaded_by.user != request.user:
        messages.error(request, "This resource has not been approved yet.")
        return redirect('resources')
    
    # Increment download count
    resource.increment_download_count()
    
    # Get file path
    file_path = resource.file.path
    
    # Check if file exists
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    
    messages.error(request, "File not found. Please contact an administrator.")
    return redirect('resource_detail', resource_id=resource.id)

@login_required
def permission_management(request):
    """Admin permission management page"""
    # Check if user has permission to manage permissions
    if not request.user.profile.can_manage_permissions():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get all roles
    roles = UserRole.objects.all().order_by('name')
    
    # Get users with custom permissions
    users_with_custom_permissions = UserProfile.objects.filter(custom_permissions=True)
    
    # Handle form submissions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_role':
            role_name = request.POST.get('role_name')
            role_description = request.POST.get('role_description')
            can_post_events = 'can_post_events' in request.POST
            can_post_store_items = 'can_post_store_items' in request.POST
            can_post_resources = 'can_post_resources' in request.POST
            is_admin = 'is_admin' in request.POST
            can_manage_permissions = 'can_manage_permissions' in request.POST
            
            # Create new role
            role = UserRole.objects.create(
                name=role_name,
                description=role_description,
                can_post_events=can_post_events,
                can_post_store_items=can_post_store_items,
                can_post_resources=can_post_resources,
                is_admin=is_admin,
                can_manage_permissions=can_manage_permissions
            )
            
            messages.success(request, f'Role "{role.name}" created successfully!')
        
        elif action == 'edit_role':
            role_id = request.POST.get('role_id')
            role = get_object_or_404(UserRole, id=role_id)
            
            role.name = request.POST.get('role_name')
            role.description = request.POST.get('role_description')
            role.can_post_events = 'can_post_events' in request.POST
            role.can_post_store_items = 'can_post_store_items' in request.POST
            role.can_post_resources = 'can_post_resources' in request.POST
            role.is_admin = 'is_admin' in request.POST
            role.can_manage_permissions = 'can_manage_permissions' in request.POST
            
            role.save()
            
            messages.success(request, f'Role "{role.name}" updated successfully!')
        
        elif action == 'delete_role':
            role_id = request.POST.get('role_id')
            role = get_object_or_404(UserRole, id=role_id)
            
            # Check if role is being used
            if role.profiles.exists():
                messages.error(request, f'Cannot delete role "{role.name}" because it is assigned to users.')
            else:
                role_name = role.name
                role.delete()
                messages.success(request, f'Role "{role_name}" deleted successfully!')
        
        elif action == 'assign_role':
            user_id = request.POST.get('user_id')
            role_id = request.POST.get('role_id')
            
            user = get_object_or_404(User, id=user_id)
            role = get_object_or_404(UserRole, id=role_id) if role_id else None
            
            # Update user's profile
            profile = user.profile
            profile.role = role
            profile.custom_permissions = False  # Reset custom permissions when assigning a role
            profile.save()
            
            messages.success(request, f'Role assigned to {user.username} successfully!')
        
        elif action == 'update_user_permissions':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            
            profile = user.profile
            profile.custom_permissions = True
            profile.can_post_events = 'can_post_events' in request.POST
            profile.can_post_store_items = 'can_post_store_items' in request.POST
            profile.can_post_resources = 'can_post_resources' in request.POST
            profile.save()
            
            messages.success(request, f'Custom permissions updated for {user.username}!')
        
        # Redirect to avoid form resubmission
        return redirect('permission_management')
    
    # Get all users for role assignment
    users = User.objects.all().order_by('username')
    
    return render(request, 'core/permission_management.html', {
        'roles': roles,
        'users': users,
        'users_with_custom_permissions': users_with_custom_permissions,
        'title': 'Permission Management'
    })

@login_required
def promote_member(request, community_slug, user_id):
    """Promote a community member to moderator"""
    community = get_object_or_404(Community, slug=community_slug)
    user_to_promote = get_object_or_404(User, id=user_id)
    
    # Get the membership
    membership = get_object_or_404(CommunityMember, community=community, user=user_to_promote)
    
    # Check if current user is an admin of the community
    try:
        current_user_membership = CommunityMember.objects.get(community=community, user=request.user)
        if current_user_membership.role != 'admin':
            messages.error(request, "You don't have permission to promote members.")
            return redirect('community_members', slug=community_slug)
    except CommunityMember.DoesNotExist:
        messages.error(request, "You are not a member of this community.")
        return redirect('community_detail', slug=community_slug)
    
    # Promote member to moderator
    membership.role = 'moderator'
    membership.save()
    
    messages.success(request, f"{user_to_promote.username} has been promoted to moderator.")
    return redirect('community_members', slug=community_slug)

@login_required
def remove_member(request, community_slug, user_id):
    """Remove a member from a community"""
    community = get_object_or_404(Community, slug=community_slug)
    user_to_remove = get_object_or_404(User, id=user_id)
    
    # Check if current user is an admin of the community
    try:
        current_user_membership = CommunityMember.objects.get(community=community, user=request.user)
        if current_user_membership.role != 'admin':
            messages.error(request, "You don't have permission to remove members.")
            return redirect('community_members', slug=community_slug)
    except CommunityMember.DoesNotExist:
        messages.error(request, "You are not a member of this community.")
        return redirect('community_detail', slug=community_slug)
    
    # Don't allow removing yourself if you're the admin
    if request.user == user_to_remove:
        messages.error(request, "You cannot remove yourself from the community.")
        return redirect('community_members', slug=community_slug)
    
    # Remove the member
    try:
        membership = CommunityMember.objects.get(community=community, user=user_to_remove)
        membership.delete()
        
        messages.success(request, f"{user_to_remove.username} has been removed from the community.")
    except CommunityMember.DoesNotExist:
        messages.error(request, f"{user_to_remove.username} is not a member of this community.")
    
    return redirect('community_members', slug=community_slug)

# def update_cart(request):
#     if request.method == 'POST':
#         product_id = request.POST.get('product_id')
#         quantity = int(request.POST.get('quantity', 1))
        
#         if 'cart' not in request.session:
#             request.session['cart'] = {}
        
#         cart = request.session['cart']
        
#         # Update quantity or remove if quantity is 0
#         if quantity > 0:
#             cart[product_id] = quantity
#         elif product_id in cart:
#             del cart[product_id]
            
#         request.session.modified = True
#         messages.success(request, 'Cart updated successfully')
    
#     return redirect('cart')



from django.http import JsonResponse

def update_cart(request):
    if request.method == 'POST':
        try:
            product_id = int(request.POST.get('product_id'))
            quantity = int(request.POST.get('quantity'))

            # Validate quantity
            if quantity < 1:
                return JsonResponse({"status": "error", "message": "Quantity must be at least 1."})

            # Get the cart from the session
            cart = request.session.get('cart', {})
            product_id_str = str(product_id)

            # Check if the product exists in the cart
            if product_id_str not in cart:
                return JsonResponse({"status": "error", "message": "Product not found in cart."})

            # Update the quantity
            cart[product_id_str] = quantity
            request.session['cart'] = cart
            request.session.modified = True

            return JsonResponse({"status": "success", "message": "Cart updated successfully."})
        except (ValueError, TypeError):
            return JsonResponse({"status": "error", "message": "Invalid input."})
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method."})





def remove_from_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        
        if 'cart' in request.session and product_id in request.session['cart']:
            del request.session['cart'][product_id]
            request.session.modified = True
            messages.success(request, 'Item removed from cart')
    
    return redirect('cart')

def clear_cart(request):
    if request.method == 'POST':
        if 'cart' in request.session:
            request.session['cart'] = {}
            request.session.modified = True
            messages.success(request, 'Cart cleared successfully')
    
    return redirect('cart')

def communities(request):
    communities_list = Community.objects.all()
    search_query = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    if search_query:
        communities_list = communities_list.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if category:
        communities_list = communities_list.filter(category=category)
    
    paginator = Paginator(communities_list, 12)  # Show 12 communities per page
    page_number = request.GET.get('page')
    communities = paginator.get_page(page_number)
    
    return render(request, 'core/communities.html', {
        'communities': communities,
        'community_categories': Community.CATEGORY_CHOICES
    })

def community_detail(request, slug):
    community = get_object_or_404(Community, slug=slug)
    
    # Check if user is a member
    is_member = False
    is_admin = False
    if request.user.is_authenticated:
        try:
            membership = CommunityMember.objects.get(community=community, user=request.user)
            is_member = True
            is_admin = membership.role == 'admin'
        except CommunityMember.DoesNotExist:
            is_member = False
            is_admin = False
    
    # Get discussions
    discussions = Discussion.objects.filter(community=community)[:5]
    
    # Get upcoming events
    current_date = timezone.now().date()  # Convert to date for proper comparison
    upcoming_events = Event.objects.filter(
        community=community,
        end_date__gte=current_date
    ).order_by('start_date')[:4]
    
    # Get community admins and moderators
    admins = User.objects.filter(
        community_memberships__community=community,
        community_memberships__role__in=['admin', 'moderator']
    ).distinct()
    
    # Get members for sidebar (limit to 5)
    members = User.objects.filter(
        community_memberships__community=community
    ).distinct()[:5]
    
    # Get related communities (same category, exclude current)
    related_communities = Community.objects.filter(
        category=community.category
    ).exclude(id=community.id)[:3]
    
    return render(request, 'core/community_detail.html', {
        'community': community,
        'is_member': is_member,
        'is_admin': is_admin,
        'discussions': discussions,
        'events': upcoming_events,
        'admins': admins,
        'members': members,
        'related_communities': related_communities,
        'discussions_page_obj': discussions,  # For has_other_pages check
        'events_page_obj': upcoming_events,  # For has_other_pages check
    })

@login_required
def join_community(request, slug):
    community = get_object_or_404(Community, slug=slug)
    
    # Check if already a member
    if CommunityMember.objects.filter(community=community, user=request.user).exists():
        messages.info(request, f'You are already a member of {community.name}')
    else:
        CommunityMember.objects.create(
            community=community,
            user=request.user,
            role='member'
        )
        messages.success(request, f'You have joined {community.name}!')
    
    return redirect('community_detail', slug=community.slug)

@login_required
def leave_community(request, slug):
    community = get_object_or_404(Community, slug=slug)
    
    # Get membership if exists
    membership = CommunityMember.objects.filter(community=community, user=request.user).first()
    
    if membership:
        # Check if user is the only admin
        if membership.role == 'admin':
            admin_count = CommunityMember.objects.filter(
                community=community, 
                role='admin'
            ).count()
            
            if admin_count <= 1:
                messages.error(
                    request, 
                    'You cannot leave the community as you are the only admin. '
                    'Please assign another admin first.'
                )
                return redirect('community_detail', slug=community.slug)
        
        # Delete membership
        membership.delete()
        messages.success(request, f'You have left {community.name}')
    else:
        messages.info(request, f'You are not a member of {community.name}')
    
    return redirect('communities')

@login_required
def edit_community(request, slug):
    community = get_object_or_404(Community, slug=slug)
    
    # Check if user is admin
    try:
        membership = CommunityMember.objects.get(community=community, user=request.user)
        if membership.role != 'admin':
            messages.error(request, 'You must be an admin to edit this community')
            return redirect('community_detail', slug=community.slug)
    except CommunityMember.DoesNotExist:
        messages.error(request, 'You must be a community admin to edit it')
        return redirect('community_detail', slug=community.slug)
    
    if request.method == 'POST':
        form = CommunityEditForm(request.POST, request.FILES, instance=community)
        if form.is_valid():
            form.save()
            messages.success(request, f'{community.name} updated successfully!')
            return redirect('community_detail', slug=community.slug)
    else:
        form = CommunityEditForm(instance=community)
    
    return render(request, 'core/community_form.html', {
        'form': form,
        'title': f'Edit {community.name}',
        'community': community,
    })

@login_required
def community_members(request, slug):
    community = get_object_or_404(Community, slug=slug)
    
    # Check if user is a member
    is_member = CommunityMember.objects.filter(community=community, user=request.user).exists()
    
    # Get member list
    members = CommunityMember.objects.filter(community=community).select_related('user')
    
    # Check if user is admin
    is_admin = CommunityMember.objects.filter(
        community=community, 
        user=request.user,
        role='admin'
    ).exists()
    
    return render(request, 'core/community_members.html', {
        'community': community,
        'members': members,
        'is_member': is_member,
        'is_admin': is_admin,
    })

# Discussion views
@login_required
def create_discussion(request, community_slug):
    community = get_object_or_404(Community, slug=community_slug)
    
    # Check if user is a member
    try:
        membership = CommunityMember.objects.get(community=community, user=request.user)
        is_member = True
    except CommunityMember.DoesNotExist:
        is_member = False
        
    if not is_member:
        messages.error(request, 'You must be a member to create discussions')
        return redirect('community_detail', slug=community.slug)
    
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.community = community
            discussion.created_by = request.user
            
            # Generate slug
            base_slug = slugify(discussion.title)
            unique_slug = base_slug
            counter = 1
            
            while Discussion.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            discussion.slug = unique_slug
            discussion.save()
            
            messages.success(request, 'Discussion created successfully!')
            return redirect('discussion_detail', community_slug=community.slug, slug=discussion.slug)
    else:
        form = DiscussionForm()
    
    return render(request, 'core/discussion_form.html', {
        'form': form,
        'community': community,
        'title': 'Create Discussion'
    })

def community_discussions(request, slug):
    community = get_object_or_404(Community, slug=slug)
    
    # Check if user is a member
    is_member = CommunityMember.objects.filter(community=community, user=request.user).exists()
    
    # Get all discussions
    discussions_list = Discussion.objects.filter(community=community)
    
    # Pagination
    paginator = Paginator(discussions_list, 10)
    page_number = request.GET.get('page')
    discussions = paginator.get_page(page_number)
    
    return render(request, 'core/community_discussions.html', {
        'community': community,
        'discussions': discussions,
        'is_member': is_member,
    })

def discussion_detail(request, community_slug, slug):
    community = get_object_or_404(Community, slug=community_slug)
    discussion = get_object_or_404(Discussion, slug=slug, community=community)
    
    # Increment view count
    discussion.view_count += 1
    discussion.save()
    
    # Check if user is a member
    is_member = False
    is_discussion_owner = False
    is_admin = False
    
    if request.user.is_authenticated:
        try:
            membership = CommunityMember.objects.get(community=community, user=request.user)
            is_member = True
            is_admin = membership.role == 'admin'
        except CommunityMember.DoesNotExist:
            is_member = False
        
        # Check if user is the discussion creator
        is_discussion_owner = (discussion.created_by == request.user)
    
    # Handle comment form
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.discussion = discussion
            comment.created_by = request.user
            comment.save()
            messages.success(request, 'Comment added successfully')
            return redirect('discussion_detail', community_slug=community.slug, slug=discussion.slug)
    else:
        form = CommentForm()
    
    # Get comments
    comments = Comment.objects.filter(discussion=discussion)
    
    return render(request, 'core/discussion_detail.html', {
        'community': community,
        'discussion': discussion,
        'comments': comments,
        'form': form,
        'is_member': is_member,
        'is_discussion_owner': is_discussion_owner,
        'is_admin': is_admin,
    })

# Event views
@login_required
def create_event(request, community_slug):
    community = get_object_or_404(Community, slug=community_slug)
    
    # Check if user is an admin of the community
    try:
        membership = CommunityMember.objects.get(community=community, user=request.user)
        if membership.role != 'admin':
            messages.error(request, 'Only community administrators can create events')
            return redirect('community_detail', slug=community.slug)
    except CommunityMember.DoesNotExist:
        messages.error(request, 'You must be a community administrator to create events')
        return redirect('community_detail', slug=community.slug)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.community = community
            event.created_by = request.user
            
            # Generate slug
            base_slug = slugify(event.title)
            unique_slug = base_slug
            counter = 1
            
            while Event.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            event.slug = unique_slug
            event.save()
            
            # Add creator as attendee
            EventAttendee.objects.create(
                event=event,
                user=request.user
            )
            
            messages.success(request, 'Event created successfully!')
            return redirect('event_detail', community_slug=community.slug, slug=event.slug)
    else:
        form = EventForm()
    
    return render(request, 'core/event_form.html', {
        'form': form,
        'community': community,
        'title': 'Create Event'
    })

@login_required
def community_events(request, slug):
    community = get_object_or_404(Community, slug=slug)
    
    # Check if user is a member
    is_member = False
    if request.user.is_authenticated:
        is_member = CommunityMember.objects.filter(community=community, user=request.user).exists()
    
    # Get upcoming events
    current_date = timezone.now().date()  # Convert to date for proper comparison
    upcoming_events = Event.objects.filter(
        community=community,
        end_date__gte=current_date
    ).order_by('start_date')
    
    # Get past events
    current_date = timezone.now().date()  # Convert to date for proper comparison
    past_events = Event.objects.filter(
        community=community,
        end_date__lt=current_date
    ).order_by('-start_date')
    
    # Pagination for upcoming events
    upcoming_paginator = Paginator(upcoming_events, 6)
    upcoming_page = request.GET.get('upcoming_page')
    upcoming = upcoming_paginator.get_page(upcoming_page)
    
    # Pagination for past events
    past_paginator = Paginator(past_events, 6)
    past_page = request.GET.get('past_page')
    past = past_paginator.get_page(past_page)
    
    return render(request, 'core/community_events.html', {
        'community': community,
        'upcoming_events': upcoming,
        'past_events': past,
        'is_member': is_member,
    })

@login_required
def community_event_detail(request, community_slug, slug):
    community = get_object_or_404(Community, slug=community_slug)
    event = get_object_or_404(Event, slug=slug, community=community)
    
    # Check if user is a member
    is_member = False
    is_attending = False
    
    if request.user.is_authenticated:
        is_member = CommunityMember.objects.filter(community=community, user=request.user).exists()
        is_attending = EventAttendee.objects.filter(event=event, user=request.user).exists()
    
    # Get attendees
    attendees = User.objects.filter(events_attending__event=event)
    
    return render(request, 'core/event_detail.html', {
        'community': community,
        'event': event,
        'attendees': attendees,
        'is_member': is_member,
        'is_attending': is_attending,
    })

@login_required
def attend_event(request, community_slug, slug):
    community = get_object_or_404(Community, slug=community_slug)
    event = get_object_or_404(Event, slug=slug, community=community)
    
    # Check if already attending
    if EventAttendee.objects.filter(event=event, user=request.user).exists():
        messages.info(request, f'You are already registered for {event.title}')
    else:
        EventAttendee.objects.create(
            event=event,
            user=request.user
        )
        messages.success(request, f'You have registered for {event.title}!')
    
    return redirect('event_detail', community_slug=community.slug, slug=event.slug)

@login_required
def leave_event(request, community_slug, slug):
    community = get_object_or_404(Community, slug=community_slug)
    event = get_object_or_404(Event, slug=slug, community=community)
    
    # Check if attending
    attendance = EventAttendee.objects.filter(event=event, user=request.user).first()
    
    if attendance:
        attendance.delete()
        messages.success(request, f'You have unregistered from {event.title}')
    else:
        messages.info(request, f'You are not registered for {event.title}')
    
    return redirect('event_detail', community_slug=community.slug, slug=event.slug)

@login_required
def create_community(request):
    if request.method == 'POST':
        form = CommunityForm(request.POST, request.FILES)
        if form.is_valid():
            community = form.save(commit=False)
            community.created_by = request.user
            community.save()
            
            # Add creator as admin
            CommunityMember.objects.create(
                community=community,
                user=request.user,
                role='admin'
            )
            
            messages.success(request, f'Community "{community.name}" created successfully!')
            return redirect('community_detail', slug=community.slug)
    else:
        form = CommunityForm()
    
    return render(request, 'core/community_form.html', {
        'form': form,
        'title': 'Create Community'
    })

@login_required
def search(request):
    query = request.GET.get('q', '')
    if query:
        events = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
        posts = BlogPost.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        )
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    else:
        events = []
        posts = []
        products = []

    context = {
        'query': query,
        'events': events,
        'posts': posts,
        'products': products,
    }
    return render(request, 'core/search.html', context)

@login_required
def process_membership(request):
    if request.method == 'POST':
        try:
            tier = request.POST.get('tier')
            amount = float(request.POST.get('amount'))
            payment_method = request.POST.get('payment_method')
            
            # Get user profile
            try:
                profile = request.user.profile
            except UserProfile.DoesNotExist:
                messages.error(request, 'Please complete your profile first.')
                return redirect('profile')
            
            # Check if user already has an active membership
            if profile.is_membership_active():
                messages.info(request, 'You already have an active membership.')
                return redirect('membership')
            
            # Create a pending membership
            membership = Membership.objects.create(
                user=request.user,
                plan_type=tier,
                amount=amount,
                payment_method=payment_method,
                status='pending'
            )
            
            if payment_method == 'mpesa':
                # Redirect to M-Pesa payment
                return redirect('mpesa_payment', payment_id=membership.id)
            else:
                # Redirect to PayPal payment
                return redirect('paypal_payment', payment_id=membership.id)
                
        except Exception as e:
            logger.error(f"Error processing membership: {str(e)}")
            messages.error(request, 'An error occurred while processing your membership. Please try again.')
            return redirect('membership')
    
    return redirect('membership')

@login_required
def payment_success(request):
    payment_id = request.GET.get('payment_id')
    if payment_id:
        try:
            membership = Membership.objects.get(id=payment_id)
            if membership.user != request.user:
                messages.error(request, 'Invalid membership.')
                return redirect('membership')
                
            # Update membership status
            membership.status = 'completed'
            membership.is_active = True
            membership.start_date = timezone.now()
            membership.end_date = membership.start_date + timezone.timedelta(days=365)  # 1 year membership
            membership.save()
            
            # Update user profile
            try:
                profile = request.user.profile
                profile.membership_status = 'active'
                profile.membership_expiry = membership.end_date.date()
                profile.save()
                
                # Send confirmation email
                send_payment_confirmation_email(request.user, membership)
                
                messages.success(request, 'Your membership has been activated successfully!')
            except UserProfile.DoesNotExist:
                messages.warning(request, 'Membership activated but profile not found.')
        except Membership.DoesNotExist:
            messages.error(request, 'Membership not found.')
    return redirect('membership')

@login_required
def payment_cancel(request):
    payment_id = request.GET.get('payment_id')
    if payment_id:
        try:
            membership = Membership.objects.get(id=payment_id)
            if membership.user != request.user:
                messages.error(request, 'Invalid membership.')
                return redirect('membership')
                
            # Update membership status
            membership.status = 'cancelled'
            membership.is_active = False
            membership.save()
            
            # Update user profile if needed
            try:
                profile = request.user.profile
                if profile.membership_status == 'active' and profile.membership_expiry:
                    # Only update if this was the active membership
                    if profile.membership_expiry == membership.end_date.date():
                        profile.membership_status = 'inactive'
                        profile.membership_expiry = None
                        profile.save()
            except UserProfile.DoesNotExist:
                pass
                
            messages.warning(request, 'Your membership payment was cancelled.')
        except Membership.DoesNotExist:
            messages.error(request, 'Membership not found.')
    return redirect('membership')

@login_required
def store(request):
    """Display all products in the store"""
    products = Product.objects.filter(is_active=True)
    
    # Get filter parameters from URL
    category = request.GET.get('category')
    sort = request.GET.get('sort', 'latest')
    search = request.GET.get('q')
    
    # Apply category filter if specified
    if category:
        products = products.filter(category=category)
    
    # Apply search filter if specified
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Apply sorting
    if sort == 'price-low':
        products = products.order_by('price')
    elif sort == 'price-high':
        products = products.order_by('-price')
    elif sort == 'popular':
        products = products.order_by('-view_count')
    else:  # Added missing colon here
        # Default to latest
        products = products.order_by('-created_at')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 12)  # Show 12 products per page
    
    try:
        paginated_products = paginator.page(page)
    except:
        paginated_products = paginator.page(1)
    
    return render(request, 'core/store.html', {
        'products': paginated_products,
        'category': category,
        'sort': sort,
        'search_query': search,
        'title': 'Store'
    })

def constitution(request):
    """Render the ESA constitution page"""
    return render(request, 'core/constitution.html')

def esa_journals(request):
    """
    ESA Journals page - similar to blog but with ESA blogs shown first
    Prioritizes journals
    """
    # Get filter parameters from URL
    category = request.GET.get('category', 'journal')  # Default to journal category for ESA journals
    sort = request.GET.get('sort', 'latest')
    search = request.GET.get('search')
    year = request.GET.get('year')
    
    try:
        # Base queryset - only published posts
        # For ESA journals, default to the journal category
        posts = BlogPost.objects.filter(is_published=True)
        
        # Make sure ESA authored posts appear first in the results
        # This assumes you have some way to identify ESA authored posts
        # For example, if you have special authors for ESA or a special tag
        # Here we're using a simple approach by putting posts with "ESA" in the title first
        posts = list(posts)
        posts.sort(key=lambda p: 0 if "ESA" in p.title else 1)
        
        # Apply category filter
        if category:
            posts = [p for p in posts if p.category == category]
        
        # Apply search filter
        if search:
            posts = [p for p in posts if search.lower() in p.title.lower() or search.lower() in p.content.lower()]
            
        # Apply year filter (for journal archives)
        if year:
            posts = [p for p in posts if p.created_at.year == int(year)]
            
    except Exception as e:
        print(f"Database error: {e}")
        posts = []
    
    # Get recent posts for sidebar
    try:
        recent_posts = BlogPost.objects.filter(is_published=True).order_by('-created_at')[:5]
    except Exception as e:
        print(f"Error getting recent posts: {e}")
        recent_posts = []
    
    # Get all categories for the sidebar filter
    categories = [choice[0] for choice in BlogPost.CATEGORY_CHOICES]
    
    # Count posts per category
    category_counts = {}
    for cat in categories:
        try:
            category_counts[cat] = BlogPost.objects.filter(category=cat, is_published=True).count()
        except Exception:
            category_counts[cat] = 0
    
    context = {
        'posts': posts,
        'recent_posts': recent_posts,
        'category': category,
        'sort': sort,
        'search': search,
        'year': year,
        'categories': categories,
        'category_counts': category_counts,
        'is_journals_page': True,  # Flag to indicate we're on the journals page
        'title': 'ESA Journals',  # Custom title for the page
    }
    return render(request, 'core/blog.html', context)

def more_sites(request):
    """Render the More Sites page with links to other relevant engineering sites"""
    # Fetch approved external sites grouped by type
    university_clubs = ExternalSite.objects.filter(site_type='university', is_approved=True)
    community_links = ExternalSite.objects.filter(site_type='community', is_approved=True)
    partner_sites = ExternalSite.objects.filter(site_type='partner', is_approved=True)
    
    context = {
        'title': 'Engineering Resources & Links',
        'university_clubs': university_clubs,
        'community_links': community_links,
        'sites': partner_sites
    }
    return render(request, 'core/more_sites.html', context)

def suggest_resource(request):
    """Handle suggestions for new resource links from users"""
    if request.method == 'POST':
        name = request.POST.get('name')
        url = request.POST.get('url')
        description = request.POST.get('description')
        category = request.POST.get('category')
        icon = request.POST.get('icon', '')
        
        if name and url and description and category:
            # Map form category to site_type
            site_type_mapping = {
                'education': 'community',
                'professional': 'partner',
                'organization': 'partner',
                'university': 'university',
                'other': 'community',
                'partner': 'partner',  # Direct mapping from site_form radio buttons
                'community': 'community'  # Direct mapping from site_form radio buttons
            }
            site_type = site_type_mapping.get(category, 'community')
            
            # Create a new ExternalSite object
            from .models import ExternalSite
            
            # Create and save the site suggestion
            site = ExternalSite(
                name=name,
                url=url,
                description=description,
                site_type=site_type,
                icon=icon,
                added_by=request.user,
                is_approved=False  # Requires admin approval
            )
            site.save()
            
            messages.success(request, 'Thank you for suggesting this connection! It will be reviewed by an administrator.')
        else:
            messages.error(request, 'Please fill in all the required fields.')
            
    return redirect('more_sites')

@login_required
def add_resource_link(request):
    """Allow authenticated users to add resource links"""
    # For GET requests, direct user to the appropriate form based on request
    return redirect('site_form')

def donate(request):
    """Render the donation page for ESA with various donation options"""
    # TEMPORARY: Redirect to payment coming soon instead of processing donations
    # TODO: When M-Pesa credentials are configured, uncomment the original code below and comment out this redirect
    if request.method == 'POST':
        messages.info(request, 'Payment functionality is coming soon. We\'re currently configuring our payment system.')
        return redirect('payment_coming_soon')
    
    # ORIGINAL DONATION CODE - UNCOMMENT WHEN PAYMENT IS READY:
    # if request.method == 'POST':
    #     payment_method = request.POST.get('payment_method')
    #     
    #     if payment_method == 'card':
    #         messages.info(request, "Credit/Debit Card payments will be available soon. Currently only M-PESA is supported.")
    #         return render(request, 'core/donate.html')
    #     
    #     elif payment_method == 'bank':
    #         messages.info(request, "Bank Transfer payments will be available soon. Currently only M-PESA is supported.")
    #         return render(request, 'core/donate.html')
    #         
    #     elif payment_method != 'mpesa':
    #         messages.info(request, f"{payment_method.title()} payments will be available soon. Currently only M-PESA is supported.")
    #         return render(request, 'core/donate.html')
    #     
    #     # Process M-Pesa payment
    #     phone_number = request.POST.get('phone')
    #     amount = request.POST.get('amount')
    #     name = request.POST.get('name')
    #     email = request.POST.get('email')
    #     donation_purpose = request.POST.get('donation_purpose', 'general')
    #     message = request.POST.get('message', '')
    #     anonymous = request.POST.get('anonymous', False)
    #     
    #     if not phone_number or not amount:
    #         messages.error(request, "Please provide both phone number and amount for M-PESA payment.")
    #         return render(request, 'core/donate.html')
    #         
    #     try:
    #         # Create a payment record
    #         payment = Payment.objects.create(
    #             user=request.user if request.user.is_authenticated else None,
    #             amount=amount,
    #             currency='KES',
    #             payment_method='mpesa',
    #             status='pending',
    #             notes=f"Donation: {donation_purpose} - {message} - {'Anonymous' if anonymous else name}"
    #         )
    #         
    #         # Redirect to M-Pesa payment page
    #         return redirect('donate_mpesa', payment_id=payment.id)
    #     except Exception as e:
    #         messages.error(request, f"An error occurred: {str(e)}")
    #         return render(request, 'core/donate.html')
    
    return render(request, 'core/donate.html')

def donate_mpesa(request, payment_id):
    """Handle M-Pesa payment for donations"""
    try:
        payment = Payment.objects.get(id=payment_id)
        
        if request.method == 'POST':
            phone_number = request.POST.get('phone_number')
            
            if not phone_number:
                messages.error(request, "Please provide your M-Pesa phone number.")
                return render(request, 'core/donate_mpesa.html', {'payment': payment})
            
            # Initialize M-Pesa payment service
            mpesa_service = MpesaService()
            
            try:
                # Initiate STK push
                response = mpesa_service.initiate_stk_push(
                    phone_number=phone_number,
                    amount=payment.amount,
                    reference=f"ESA-Donation-{payment.id}",
                    description="ESA-KU Donation"
                )
                
                # Update payment with M-Pesa transaction details
                mpesa_transaction = MpesaTransaction.objects.create(
                    payment=payment,
                    phone_number=phone_number,
                    amount=payment.amount,
                    status='pending'
                )
                
                messages.success(request, "M-Pesa payment initiated. Please check your phone to complete the transaction.")
                return redirect('donation_pending', payment_id=payment.id)
                
            except Exception as e:
                messages.error(request, f"Failed to initiate M-Pesa payment: {str(e)}")
                return render(request, 'core/donate_mpesa.html', {'payment': payment})
        
        # GET request - show the payment form
        context = {
            'payment': payment,
            'form': MpesaPaymentForm(),
        }
        return render(request, 'core/donate_mpesa.html', context)
        
    except Payment.DoesNotExist:
        messages.error(request, "Payment not found.")
        return redirect('donate')

def donation_pending(request, payment_id):
    """Show pending donation status"""
    try:
        payment = Payment.objects.get(id=payment_id)
        return render(request, 'core/donation_pending.html', {'payment': payment})
    except Payment.DoesNotExist:
        messages.error(request, "Payment not found.")
        return redirect('donate')

def donation_success(request):
    """Show donation success page"""
    payment_id = request.GET.get('payment_id')
    
    try:
        if payment_id:
            payment = Payment.objects.get(id=payment_id)
        else:
            messages.error(request, "Payment information not found.")
            return redirect('donate')
            
        return render(request, 'core/donation_success.html', {'payment': payment})
    except Payment.DoesNotExist:
        messages.error(request, "Payment not found.")
        return redirect('donate')
            
    except Exception as e:
        messages.error(request, f"Failed to process donation: {str(e)}")
        
    return render(request, 'core/donate.html')

@login_required
def member_get_member(request):
    """
    Member-Get-Member referral program view
    Allows members to pay for someone else's membership
    """
    # TEMPORARY: Redirect to payment coming soon instead of processing member-get-member
    # TODO: When M-Pesa credentials are configured, uncomment the original code below and comment out this redirect
    messages.info(request, 'Payment functionality is coming soon. We\'re currently configuring our payment system.')
    return redirect('payment_coming_soon')
    
    # ORIGINAL MEMBER-GET-MEMBER CODE - UNCOMMENT WHEN PAYMENT IS READY:
    # try:
    #     profile = request.user.profile
    # except UserProfile.DoesNotExist:
    #     messages.error(request, 'Please complete your profile first.')
    #     return redirect('profile')
    #     
    # # Check if user is an active member
    # if not profile.is_membership_active():
    #     messages.info(request, 'You need to be an active member to participate in the referral program.')
    #     return redirect('membership')
    # 
    # # Get membership plans for the form
    # plans = MembershipPlan.objects.filter(is_active=True)
    # 
    # # Get referrals by this user
    # referrals = Membership.objects.filter(referred_by=request.user)
    # 
    # if request.method == 'POST':
    #     form = MemberGetMemberForm(request.POST)
    #     if form.is_valid():
    #         referred_email = form.cleaned_data.get('referred_email')
    #         student_id = form.cleaned_data.get('student_id')
    #         plan_type = form.cleaned_data.get('plan_type')
    #         payment_method = form.cleaned_data.get('payment_method')
    #         phone_number = form.cleaned_data.get('phone_number')
    #         
    #         # Debug logging
    #         logger.info(f"Processing member-get-member request: email={referred_email}, plan={plan_type}, payment={payment_method}")
    #         
    #         try:
    #             # Get the referred user
    #             logger.info(f"Looking up user with email: {referred_email}")
    #             referred_user = User.objects.get(email=referred_email)
    #             logger.info(f"Found user: {referred_user.username}")
    #             
    #             # Validate student_id matches the user's profile
    #             logger.info(f"Validating student_id: {student_id}")
    #             try:
    #                 user_profile = referred_user.profile
    #                 if user_profile.student_id != student_id:
    #                     logger.error(f"Student ID mismatch: provided={student_id}, actual={user_profile.student_id}")
    #                     messages.error(request, f'Student ID "{student_id}" does not match the user with email "{referred_email}". Please verify both email and student ID.')
    #                     return render(request, 'core/member_get_member.html', {
    #                         'form': form,
    #                         'plans': plans
    #                     })
    #                     logger.info(f"Student ID validation passed: {student_id}")
    #                 except UserProfile.DoesNotExist:
    #                     logger.error(f"User {referred_user.username} does not have a profile")
    #                     messages.error(request, f'User with email "{referred_email}" does not have a complete profile. They need to complete their profile first.')
    #                     return render(request, 'core/member_get_member.html', {
    #                         'form': form,
    #                         'plans': plans
    #                     })
    #                 
    #                 # Get the membership plan that matches the selected plan_type
    #                 logger.info(f"Looking up membership plan: {plan_type}")
    #                 try:
    #                     plan = MembershipPlan.objects.get(plan_type=plan_type, is_active=True)
    #                     logger.info(f"Found plan: {plan.name} - KSh {plan.price}")
    #                 except MembershipPlan.DoesNotExist:
    #                     logger.error(f"No active membership plan found for {plan_type}")
    #                     messages.error(request, f'No active membership plan found for {plan_type}. Please contact support.')
    #                     return redirect('member_get_member')
    #                 
    #                 # Check if the referred user already has an active membership
    #                 logger.info(f"Checking for existing active membership for user: {referred_user.username}")
    #                 existing_membership = Membership.objects.filter(
    #                     user=referred_user, 
    #                     is_active=True
    #                 ).first()
    #                 
    #                 if existing_membership:
    #                     logger.warning(f"User {referred_user.username} already has active membership")
    #                     messages.warning(request, f'{referred_user.get_full_name()} already has an active membership.')
    #                     return redirect('member_get_member')
    #                 
    #                 # Create a payment record for the referred user
    #                 logger.info(f"Creating payment record for user: {referred_user.username}")
    #                 payment = Payment.objects.create(
    #                     user=referred_user,
    #                     amount=plan.price,
    #                     payment_method=payment_method,
    #                     status='pending',
    #                     notes=f"ESA-KU Membership Payment for {plan.get_plan_type_display()} - Paid by {request.user.get_full_name()}"
    #                 )
    #                 logger.info(f"Created payment: {payment.id}")
    #                 
    #                 # Calculate end date
    #                 start_date = timezone.now().date()
    #                 try:
    #                     end_date = start_date + relativedelta(months=plan.duration)
    #                     logger.info(f"Calculated end date: {end_date}")
    #                 except Exception as e:
    #                     logger.error(f"Error calculating end date: {str(e)}")
    #                     messages.error(request, 'An error occurred while processing your request. Please try again.')
    #                     return redirect('member_get_member')
    #                 
    #                 # Create membership record
    #                 logger.info(f"Creating membership record for user: {referred_user.username}")
    #                 membership = Membership.objects.create(
    #                     user=referred_user,
    #                     plan=plan,
    #                     start_date=start_date,
    #                     end_date=end_date,
    #                     status='pending',
    #                     payment=payment,
    #                     referred_by=request.user
    #                 )
    #                 logger.info(f"Created membership: {membership.id}")
    #                 
    #                 # Send initial notification email
    #                 logger.info(f"Sending notification email to: {referred_user.email}")
    #                 try:
    #                     from core.email_service import send_gift_membership_notification
    #                     send_gift_membership_notification(referred_user, request.user)
    #                     logger.info("Notification email sent successfully")
    #                 except Exception as e:
    #                     logger.error(f"Error sending notification email: {str(e)}")
    #                     # Don't fail the whole process if email fails
    #                 
    #                 messages.success(request, f'Gift membership initiated for {referred_user.get_full_name()}. Please complete the payment to activate their membership.')
    #                 
    #                 # Redirect to appropriate payment method
    #                 if payment_method == 'mpesa':
    #                     return redirect('mgm_mpesa_payment', payment_id=payment.id)
    #                 elif payment_method == 'paypal':
    #                     return redirect('mgm_paypal_payment', payment_id=payment.id)
    #                 else:
    #                     messages.error(request, 'Invalid payment method selected.')
    #                     return redirect('member_get_member')
    #                     
    #             except User.DoesNotExist:
    #                 logger.error(f"No user found with email: {referred_email}")
    #                 messages.error(request, f'No user found with email "{referred_email}". Please ask them to register first.')
    #                 return render(request, 'core/member_get_member.html', {
    #                     'form': form,
    #                     'plans': plans
    #                 })
    #             except Exception as e:
    #                 logger.error(f"Error processing member-get-member request: {str(e)}")
    #                 messages.error(request, 'An error occurred while processing your request. Please try again.')
    #                 return redirect('member_get_member')
    #         else:
    #             logger.error(f"Form validation failed: {form.errors}")
    #             for field, errors in form.errors.items():
    #                 for error in errors:
    #                     messages.error(request, f"{field}: {error}")
    #     else:
    #         form = MemberGetMemberForm()
    #     
    #     return render(request, 'core/member_get_member.html', {
    #         'form': form,
    #         'plans': plans,
    #         'referrals': referrals
    #     })

@login_required
def mgm_mpesa_payment(request, payment_id):
    """Handle M-Pesa payment for Member-Get-Member referrals"""
    payment = get_object_or_404(Payment, id=payment_id, status='pending')
    
    # Check if this payment is for a member-get-member scenario
    try:
        membership = Membership.objects.get(payment=payment)
        if not membership.referred_by:
            messages.error(request, 'Invalid payment')
            return redirect('member_get_member')
    except Membership.DoesNotExist:
        messages.error(request, 'Invalid payment')
        return redirect('member_get_member')
    
    if payment.payment_method != 'mpesa':
        messages.error(request, 'Invalid payment method')
        return redirect('member_get_member')
    
    if request.method == 'POST':
        form = MpesaPaymentForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            amount = payment.amount
            
            # Create reference for the transaction
            reference = f"ESA-MGM-{payment.id}"
            description = f"ESA-KU Member-Get-Member Payment: {membership.get_plan_type_display()}"
            
            # Create M-Pesa transaction record
            mpesa_tx = MpesaTransaction.objects.create(
                payment=payment,
                phone_number=phone_number,
                amount=amount,
                status='pending'
            )
            
            # Initiate M-Pesa STK push
            mpesa_service = MpesaService()
            try:
                response = mpesa_service.initiate_stk_push(
                    phone_number=phone_number,
                    amount=int(amount),
                    reference=reference,
                    description=description
                )
                
                if 'CheckoutRequestID' in response:
                    # Update M-Pesa transaction with checkout request ID
                    mpesa_tx.checkout_request_id = response['CheckoutRequestID']
                    mpesa_tx.save(update_fields=['checkout_request_id'])
                    
                    messages.success(request, 'M-Pesa payment request sent to your phone. Please check your phone and enter your PIN to complete the payment.')
                    return redirect('payment_status', payment_id=payment.id)
                else:
                    messages.error(request, f'M-Pesa payment failed: {response.get("errorMessage", "Unknown error")}')
                    
            except Exception as e:
                logger.error(f"M-Pesa payment error: {str(e)}")
                messages.error(request, 'Failed to initiate M-Pesa payment. Please try again.')
    else:
        # Initialize form without phone number since Payment model doesn't have it
        form = MpesaPaymentForm()
    
    try:
        return render(request, 'core/mpesa_payment.html', {
            'payment': payment,
            'form': form,
            'membership': membership,
            'is_mgm': True
        })
    except Exception as e:
        logger.error(f"Error rendering M-Pesa payment template: {str(e)}", exc_info=True)
        messages.error(request, f'Error loading payment page: {str(e)}')
        return redirect('member_get_member')

@login_required
def mgm_paypal_payment(request, payment_id):
    """Handle PayPal payment for Member-Get-Member referrals"""
    payment = get_object_or_404(Payment, id=payment_id, status='pending')
    
    # Check if this payment is for a member-get-member scenario
    try:
        membership = Membership.objects.get(payment=payment)
        if not membership.referred_by:
            messages.error(request, 'Invalid payment')
            return redirect('member_get_member')
    except Membership.DoesNotExist:
        messages.error(request, 'Invalid payment')
        return redirect('member_get_member')
    
    if payment.payment_method != 'paypal':
        messages.error(request, 'Invalid payment method')
        return redirect('member_get_member')
    
    # Create PayPal order
    paypal_service = PayPalService()
    
    # Convert KES to USD for PayPal (simplified conversion - in production use a real exchange rate)
    amount_usd = round(float(payment.amount) / 130, 2)  # Approximate KES to USD conversion
    
    return_url = request.build_absolute_uri(reverse('mgm_paypal_success', kwargs={'payment_id': payment.id}))
    cancel_url = request.build_absolute_uri(reverse('mgm_paypal_cancel', kwargs={'payment_id': payment.id}))
    
    response = paypal_service.create_order(
        amount=amount_usd,
        currency='USD',
        reference=f"ESA-MGM-{payment.id}",
        return_url=return_url,
        cancel_url=cancel_url
    )
    
    # Store payment token for later verification
    if 'id' in response:
        payment.payment_token = response['id']
        payment.save(update_fields=['payment_token'])
        
        # Find the approval URL
        for link in response['links']:
            if link['rel'] == 'approve':
                return redirect(link['href'])
    
    messages.error(request, f"Failed to initiate PayPal payment: {json.dumps(response)}")
    return redirect('member_get_member')

@login_required
def mgm_paypal_success(request, payment_id):
    """Handle successful PayPal payment for MGM referrals"""
    payment = get_object_or_404(Payment, id=payment_id, status='pending')
    
    # Check if this payment is for a member-get-member scenario
    try:
        membership = Membership.objects.get(payment=payment)
        if not membership.referred_by:
            messages.error(request, 'Invalid payment')
            return redirect('member_get_member')
    except Membership.DoesNotExist:
        messages.error(request, 'Invalid payment')
        return redirect('member_get_member')
    
    # Get the order ID from the URL
    order_id = request.GET.get('token')
    
    if order_id and order_id == payment.payment_token:
        # Capture the payment
        paypal_service = PayPalService()
        response = paypal_service.capture_order(order_id)
        
        if 'status' in response and response['status'] == 'COMPLETED':
            # Update payment and membership
            payment.status = 'completed'
            payment.transaction_id = order_id
            payment.save(update_fields=['status', 'transaction_id'])
            
            # Activate membership
            payment.complete_payment(order_id)
            
            messages.success(request, f'Payment completed successfully! {membership.user.get_full_name()}\'s membership is now active.')
            return redirect('member_get_member')
    
    messages.error(request, 'Failed to complete payment. Please try again or contact support.')
    return redirect('member_get_member')

@login_required
def mgm_paypal_cancel(request, payment_id):
    """Handle cancelled PayPal payment for MGM referrals"""
    payment = get_object_or_404(Payment, id=payment_id, status='pending')
    
    # Check if this payment is for a member-get-member scenario
    try:
        membership = Membership.objects.get(payment=payment)
        if not membership.referred_by:
            messages.error(request, 'Invalid payment')
            return redirect('member_get_member')
    except Membership.DoesNotExist:
        messages.error(request, 'Invalid payment')
        return redirect('member_get_member')
    
    # Update payment status
    payment.status = 'cancelled'
    payment.save(update_fields=['status'])
    
    # Update membership status
    membership.status = 'cancelled'
    membership.is_active = False
    membership.save()
    
    messages.info(request, 'Payment was cancelled. The membership gift has not been processed.')
    return redirect('member_get_member')

@login_required
def admin_dashboard(request):
    """Administrative Dashboard for ESA officials and admins"""
    # Check if user has admin permissions
    if not request.user.profile.can_manage_permissions():
        messages.error(request, "You don't have permission to access the admin dashboard.")
        return redirect('home')
    
    # Get key statistics for the dashboard
    current_date = timezone.now().date()  # Convert to date for proper comparison
    stats = {
        'total_users': User.objects.count(),
        'total_members': Membership.objects.filter(is_active=True).count(),
        'upcoming_events': Event.objects.filter(end_date__gt=current_date).count(),
        'active_products': Product.objects.filter(is_active=True).count(),
        'pending_resources': Resource.objects.filter(is_approved=False).count(),
        'total_communities': Community.objects.count(),
        'newsletter_subscribers': NewsletterSubscriber.objects.count(),
    }
    
    # Get recent activities
    recent = {
        'new_members': Membership.objects.filter(is_active=True).order_by('-start_date')[:5],
        'new_resources': Resource.objects.order_by('-created_at')[:5],
        'upcoming_events': Event.objects.filter(end_date__gt=current_date).order_by('start_date')[:5],
    }
    
    # Get revenue statistics (simplified)
    revenue = {
        'total': Payment.objects.filter(status='completed').aggregate(total=models.Sum('amount'))['total'] or 0,
        'this_month': Payment.objects.filter(
            status='completed', 
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).aggregate(total=models.Sum('amount'))['total'] or 0,
    }
    
    return render(request, 'core/admin_dashboard.html', {
        'stats': stats,
        'recent': recent,
        'revenue': revenue,
        'title': 'Admin Dashboard'
    })

@login_required
def event_suggestion(request):
    """Allow users to suggest an event"""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            
            # Mark as a suggestion that needs approval
            event.status = 'suggested'
            event.is_active = False
            
            if hasattr(request.user, 'profile'):
                event.created_by = request.user
            
            event.save()
            
            # Notify admins about the event suggestion (could implement email notification here)
            
            messages.success(request, 'Your event suggestion has been submitted and will be reviewed by the ESA team!')
            return redirect('events')
    else:
        form = EventForm()
        form.fields['title'].help_text = "Provide a clear and descriptive title for your suggested event."
        form.fields['description'].help_text = "Please provide a detailed description of the event you're suggesting."
    
    return render(request, 'core/event_suggestion_form.html', {
        'form': form,
        'title': 'Suggest an Event'
    })

@login_required
def init_admin_users(request):
    """Initialize admin users for the ESA platform (one-time setup)"""
    # Only allow superusers to create admin users
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to initialize admin users.")
        return redirect('home')
    
    if request.method == 'POST':
        # Create admin role if it doesn't exist
        admin_role, created = UserRole.objects.get_or_create(
            name="ESA Admin",
            defaults={
                'description': "ESA Administrative role with full permissions",
                'is_admin': True,
                'can_post_events': True,
                'can_post_store_items': True,
                'can_post_resources': True,
                'can_manage_permissions': True
            }
        )
        
        # Get username and email from the form
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not (username and email and password):
            messages.error(request, "All fields are required.")
            return render(request, 'core/init_admin_users.html', {'title': 'Initialize Admin Users'})
            
        try:
            # Create user if doesn't exist
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_staff': True  # Give Django admin access
                }
            )
            
            if user_created:
                user.set_password(password)
                user.save()
                messages.success(request, f"User {username} created successfully.")
            else:
                messages.info(request, f"User {username} already exists.")
                
            # Create or update profile with admin role
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': admin_role,
                    'membership_status': 'active',
                    'student_id': 'ADMIN',
                    'department': 'Administration',
                    'can_post_events': True,
                    'can_post_store_items': True,
                    'can_post_resources': True
                }
            )
            
            if not profile_created:
                profile.role = admin_role
                profile.can_post_events = True
                profile.can_post_store_items = True
                profile.can_post_resources = True
                profile.save()
                
            messages.success(request, f"{username} has been set up as an ESA admin successfully.")
            
        except Exception as e:
            messages.error(request, f"Error creating admin user: {str(e)}")
            
    return render(request, 'core/init_admin_users.html', {'title': 'Initialize Admin Users'})

@login_required
def product_create(request):
    """Create a new product for the store"""
    # Check if user has permission to create store items
    if not hasattr(request.user, 'profile') or not request.user.profile.can_manage_store():
        messages.error(request, "You don't have permission to add products to the store.")
        return redirect('store')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.slug = slugify(form.cleaned_data['name'])
            
            # Set vendor_user to the current user's profile
            if hasattr(request.user, 'profile'):
                product.vendor_user = request.user.profile
            
            # Auto-approve for admins, require approval for vendors
            if request.user.profile.is_esa_admin():
                product.is_approved = True
                product.approved_by = request.user.profile
            else:
                product.is_approved = False  # Vendors need approval
            
            product.save()
            
            if product.is_approved:
                messages.success(request, f"Product '{product.name}' created successfully!")
            else:
                messages.success(request, f"Product '{product.name}' created successfully! It will be visible after admin approval.")
            
            return redirect('product_detail', slug=product.slug)
    else:
        form = ProductForm(user=request.user)
    
    return render(request, 'core/product_form.html', {
        'form': form,
        'title': 'Add New Product',
        'is_create': True
    })

@login_required
def product_edit(request, slug):
    """Edit an existing product"""
    product = get_object_or_404(Product, slug=slug)
    
    # Check if user has permission to edit this product
    can_edit = False
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        can_edit = profile.can_manage_store() or (product.created_by and product.created_by == request.user)
    
    if not can_edit:
        messages.error(request, "You don't have permission to edit this product.")
        return redirect('product_detail', slug=product.slug)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('product_detail', slug=product.slug)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'core/product_form.html', {
        'form': form,
        'product': product,
        'title': f"Edit {product.name}",
        'is_create': False
    })

@login_required
def product_delete(request, slug):
    """Delete a product"""
    product = get_object_or_404(Product, slug=slug)
    
    # Check if user has permission to delete this product
    can_delete = False
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        can_delete = profile.can_manage_store() or (product.created_by and product.created_by == request.user)
    
    if not can_delete:
        messages.error(request, "You don't have permission to delete this product.")
        return redirect('product_detail', slug=product.slug)
    
    if request.method == 'POST':
        # Delete product images if they exist
        if product.image:
            if os.path.exists(product.image.path):
                os.remove(product.image.path)
        
        product_name = product.name
        product.delete()
        messages.success(request, f"Product '{product_name}' deleted successfully!")
        return redirect('store')
    
    return render(request, 'core/product_confirm_delete.html', {
        'product': product,
        'title': f"Delete {product.name}"
    })

# def product_detail(request, slug):
#     """Display product details"""
#     product = get_object_or_404(Product, slug=slug)
    
#     # Increment view count
#     if request.session.get(f'viewed_product_{product.id}') != 'yes':
#         product.view_count = product.view_count + 1
#         product.save(update_fields=['view_count'])
#         request.session[f'viewed_product_{product.id}'] = 'yes'
    
#     # Get related products
#     related_products = Product.objects.filter(
#         category=product.category, 
#         is_active=True
#     ).exclude(id=product.id).order_by('-created_at')[:4]

#     # Check if product is in user's cart
#     in_cart = False
#     cart_quantity = 0
#     if 'cart' in request.session:
#         cart = request.session['cart']
#         product_id_str = str(product.id)
#         if product_id_str in cart:
#             in_cart = True
#             cart_quantity = cart[product_id_str]
    
#     # Check if user can edit/delete
#     can_edit = False
#     if request.user.is_authenticated and hasattr(request.user, 'profile'):
#         profile = request.user.profile
#         can_edit = profile.can_manage_store() or (product.created_by and product.created_by == request.user)

#     return render(request, 'core/product_detail.html', {
#         'product': product,
#         'related_products': related_products,
#         'in_cart': in_cart,
#         'cart_quantity': cart_quantity,
#         'can_edit': can_edit
#     })


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

def product_detail(request, slug):
    """Display product details"""
    product = get_object_or_404(Product, slug=slug)
    profile = None
    if request.user.is_authenticated:
        profile = request.user.profile

    # Handle Add to Cart form submission
    if request.method == 'POST' and 'add_to_cart' in request.POST:
        quantity = int(request.POST.get('quantity', 1))
        if quantity > product.stock:
            messages.error(request, "Requested quantity exceeds available stock.")
        else:
            cart = request.session.get('cart', {})
            product_id_str = str(product.id)
            if product_id_str in cart:
                cart[product_id_str] += quantity
            else:
                cart[product_id_str] = quantity
            request.session['cart'] = cart
            messages.success(request, f"{product.name} has been added to your cart.")
        return redirect('product_detail', slug=product.slug)

    # Increment view count
    if request.session.get(f'viewed_product_{product.id}') != 'yes':
        product.view_count = product.view_count + 1
        product.save(update_fields=['view_count'])
        request.session[f'viewed_product_{product.id}'] = 'yes'

    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).order_by('-created_at')[:4]

    # Check if product is in user's cart
    in_cart = False
    cart_quantity = 0
    if 'cart' in request.session:
        cart = request.session['cart']
        product_id_str = str(product.id)
        if product_id_str in cart:
            in_cart = True
            cart_quantity = cart[product_id_str]

    # Check if user can edit/delete
    #can_edit = False
    #if request.user.is_authenticated and hasattr(request.user, 'profile'):
    #    profile = request.user.profile
    #    can_edit = profile.can_manage_store() or (product.created_by and product.created_by == request.user)

    can_edit = profile and profile.can_manage_store()
    if hasattr(product, 'created_by'):
        can_edit = can_edit or (product.created_by == request.user)
        
    return render(request, 'core/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'in_cart': in_cart,
        'cart_quantity': cart_quantity,
        'can_edit': can_edit
    })

def cart(request):
    """Display shopping cart"""
    cart_items = []
    total = 0
    item_count = 0  # Track the total number of items in the cart

    if 'cart' in request.session:
        cart = request.session['cart']

        for product_id_str, quantity in cart.items():
            try:
                product_id = int(product_id_str)
                product = Product.objects.get(id=product_id)

                # Skip products that are no longer active or in stock
                if not product.is_active or product.stock < quantity:
                    continue

                item_total = product.price * quantity
                total += item_total
                item_count += quantity

                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'item_total': item_total
                })
            except (ValueError, Product.DoesNotExist):
                # Remove invalid product IDs from cart
                cart.pop(product_id_str, None)
                request.session.modified = True

    return render(request, 'core/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'item_count': item_count,
        'title': 'Shopping Cart'
    })
    print(request.session.get('cart', {}))



from django.shortcuts import render, redirect
from django.contrib import messages
from .services import MpesaService

@login_required
def checkout(request):
    cart_items = []
    total = 0
    item_count = 0

    if 'cart' in request.session:
        cart = request.session.get('cart', {})

        for product_id_str, quantity in cart.items():
            try:
                product_id = int(product_id_str)
                product = Product.objects.get(id=product_id)

                if not product.is_active or product.stock < quantity:
                    continue

                item_total = product.price * quantity
                total += item_total
                item_count += quantity

                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'item_total': item_total
                })
            except (ValueError, Product.DoesNotExist):
                cart.pop(product_id_str, None)
                request.session.modified = True

    if request.method == 'POST':
        # TEMPORARY: Redirect to payment coming soon instead of processing payment
        # TODO: When M-Pesa credentials are configured, uncomment the original payment processing code below and comment out this redirect
        messages.info(request, 'Payment functionality is coming soon. We\'re currently configuring our payment system.')
        return redirect('payment_coming_soon')
        
        # ORIGINAL PAYMENT PROCESSING CODE - UNCOMMENT WHEN PAYMENT IS READY:
        # payment_method = request.POST.get('payment_method')
        # 
        # # Collect shipping information
        # shipping_info = {
        #     'name': f"{request.POST.get('first_name', '')} {request.POST.get('last_name', '')}".strip(),
        #     'email': request.POST.get('email', request.user.email),
        #     'phone': request.POST.get('phone', ''),
        #     'address': request.POST.get('address', ''),
        #     'delivery_method': request.POST.get('delivery_method', 'pickup'),
        #     'student_id': request.POST.get('student_id', '')
        # }
        # 
        # if payment_method == 'mpesa':
        #     mpesa_phone = request.POST.get('mpesa_phone')
        #     if not mpesa_phone:
        #         messages.error(request, "Please enter your M-Pesa phone number.")
        #         return render(request, 'core/donate_mpesa.html', {'payment': payment})
        #     
        #     # Create the order first
        #     from core.order_service import OrderService
        #     try:
        #         # Create order with pending status
        #         order = OrderService.create_order(
        #             user=request.user.profile,
        #             cart_items=cart_items,
        #             total_amount=total,
        #             shipping_info=shipping_info
        #         )
        #         
        #         # Store order ID in session for payment completion
        #         request.session['pending_order_id'] = order.id
        #         
        #         # Check if MPESA settings are properly configured
        #         mpesa_settings_ok = all([
        #             getattr(settings, 'MPESA_CONSUMER_KEY', ''),
        #             getattr(settings, 'MPESA_CONSUMER_SECRET', ''),
        #             getattr(settings, 'MPESA_SHORTCODE', ''),
        #             getattr(settings, 'MPESA_PASSKEY', ''),
        #             getattr(settings, 'MPESA_CALLBACK_URL', '')
        #         ])
        #         
        #         if not mpesa_settings_ok:
        #             logging.error("M-Pesa settings are incomplete. Please check your environment variables.")
        #             messages.error(request, "Payment system is not properly configured. Your order has been saved, but payment cannot be processed at this time.")
        #             return redirect('order_status', order_id=order.id)
        #         
        #         # Validate the phone number
        #         if not mpesa_phone or len(mpesa_phone.strip()) < 9:
        #             messages.error(request, "Please enter a valid M-Pesa phone number.")
        #             return redirect('checkout')
        #         
        #         # Initiate M-Pesa STK Push
        #         try:
        #             mpesa_service = MpesaService()
        #             
        #             # Use the actual M-Pesa API
        #             response = mpesa_service.initiate_stk_push(
        #                 phone_number=mpesa_phone,
        #                 amount=total,
        #                 reference=f"ESA-Order-{order.id}",
        #                 description="Payment for ESA Store Order"
        #             )
        #             
        #             if response.get('ResponseCode') == '0':
        #                 # If we have a successful response, update MpesaTransaction
        #                 if hasattr(order, 'payment') and hasattr(order.payment, 'mpesa_transaction'):
        #                     mpesa_tx = order.payment.mpesa_transaction
        #                     if 'CheckoutRequestID' in response:
        #                         mpesa_tx.checkout_request_id = response['CheckoutRequestID']
        #                         mpesa_tx.save()
        #                 
        #                 messages.success(request, f"M-Pesa payment request sent to {mpesa_phone}. Please check your phone and enter your PIN to complete the payment.")
        #                 return redirect('order_status', order_id=order.id)
        #             else:
        #                 error_message = response.get('errorMessage', 'Payment request failed. Please try again.')
        #                 messages.error(request, error_message)
        #                 return redirect('checkout')
        #                 
        #         except Exception as e:
        #             logging.error(f"Error initiating M-Pesa payment: {str(e)}")
        #             messages.error(request, "An error occurred while processing your payment. Please try again.")
        #             return redirect('checkout')
        #             
        #     except Exception as e:
        #         logging.error(f"Error creating order: {str(e)}")
        #         messages.error(request, "An error occurred while creating your order. Please try again.")
        #         return redirect('checkout')
        # else:
        #     messages.error(request, "Please select a valid payment method.")
        #     return redirect('checkout')

    return render(request, 'core/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'item_count': item_count,
        #'title': 'Checkout' #uncomment this when payment is ready
    })

@login_required
def order_status(request, order_id):
    """Check order status and display details"""
    order = get_object_or_404(Order, id=order_id, user=request.user.profile)
    
    # Check for M-Pesa transaction if payment is pending
    # This logic would be similar to the payment_status view for membership payments
    if order.status == 'pending' and hasattr(order, 'payment') and order.payment.payment_method == 'mpesa':
        payment = order.payment
        if hasattr(payment, 'mpesa_transaction'):
            mpesa_tx = payment.mpesa_transaction
            
            # Only query status if we have a checkout request ID and status is still pending
            if mpesa_tx.checkout_request_id and mpesa_tx.status == 'pending' and payment.status == 'pending':
                mpesa_service = MpesaService()
                response = mpesa_service.query_transaction_status(mpesa_tx.checkout_request_id)
                
                # Process response if successful
                if 'ResultCode' in response and response['ResultCode'] == '0':
                    # Update transaction details
                    mpesa_tx.status = 'completed'
                    mpesa_tx.mpesa_receipt = response.get('MpesaReceiptNumber')
                    mpesa_tx.transaction_date = timezone.now()
                    mpesa_tx.result_code = '0'
                    mpesa_tx.result_description = response.get('ResultDesc', 'Success')
                    mpesa_tx.save()
                    
                    # Complete payment
                    payment.complete_payment(mpesa_tx.mpesa_receipt)
                    
                    # Send confirmation email
                    try:
                        from core.email_service import send_order_confirmation_email
                        send_order_confirmation_email(order.user, order)
                    except Exception as e:
                        logging.error(f"Failed to send order confirmation email: {str(e)}")
                    
                    messages.success(request, 'Your payment has been completed successfully!')
                    return redirect('order_status', order_id=order.id)
    
    # Get order items
    order_items = order.items.all()
    
    return render(request, 'core/order_status.html', {
        'order': order,
        'order_items': order_items,
        'title': f'Order #{order.id}'
    })

@login_required
@require_POST
def update_cart(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        product = get_object_or_404(Product, id=product_id)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity = quantity
            cart_item.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def blog_post_create(request):
    """Create a new blog post"""
    # All authenticated users can create blog posts
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user.profile
            
            # Only admin posts are auto-published
            if request.user.profile.is_esa_admin():
                post.is_published = True
            else:
                post.is_published = False  # Regular user posts need approval
                
            post.save()
            
            if post.is_published:
                messages.success(request, 'Blog post created and published successfully!')
            else:
                messages.success(request, 'Blog post submitted successfully! It will be reviewed by an administrator.')
            return redirect('blog_post_detail', post_id=post.id)
    else:
        form = BlogPostForm()
    
    return render(request, 'core/blog_post_form.html', {
        'form': form,
        'title': 'Create Blog Post',
        'is_create': True
    })

@login_required
def blog_post_edit(request, post_id):
    """Edit an existing blog post"""
    post = get_object_or_404(BlogPost, id=post_id)
    
    # Check if user has permission to edit this post
    if not hasattr(request.user, 'profile') or not (request.user.profile.is_esa_admin() or post.author == request.user.profile):
        messages.error(request, "You don't have permission to edit this post.")
        return redirect('blog_post_detail', post_id=post.id)
    
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blog post updated successfully!')
            return redirect('blog_post_detail', post_id=post.id)
    else:
        form = BlogPostForm(instance=post)
    
    return render(request, 'core/blog_post_form.html', {
        'form': form,
        'post': post,
        'title': 'Edit Blog Post',
        'is_create': False
    })

@login_required
def blog_post_delete(request, post_id):
    """Delete a blog post"""
    post = get_object_or_404(BlogPost, id=post_id)
    
    # Check if user has permission to delete this post
    if not hasattr(request.user, 'profile') or not (request.user.profile.is_esa_admin() or post.author == request.user.profile):
        messages.error(request, "You don't have permission to delete this post.")
        return redirect('blog_post_detail', post_id=post.id)
    
    if request.method == 'POST':
        # Delete post image if it exists
        if post.image:
            if os.path.exists(post.image.path):
                os.remove(post.image.path)
        
        post.delete()
        messages.success(request, 'Blog post deleted successfully!')
        return redirect('blog')
    
    return render(request, 'core/blog_post_confirm_delete.html', {
        'post': post,
        'title': 'Delete Blog Post'
    })

def manage_sites(request):
    """Admin view to manage submitted resource sites"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to manage sites.")
        return redirect('more_sites')
        # Get sites grouped by status
    pending_sites = ExternalSite.objects.filter(is_approved=False).order_by('-created_at')
    approved_sites = ExternalSite.objects.filter(is_approved=True).order_by('site_type', 'name')
    rejected_sites = ExternalSite.objects.filter(is_approved=False, is_rejected=True).order_by('-created_at')
    
   
    
    context = {
        'pending_sites': pending_sites,
        'approved_sites': approved_sites,
        'rejected_sites': rejected_sites,
        'title': 'Manage External Sites'
    }
    
    return render(request, 'core/manage_sites.html', context)

def more_sites(request):
    """Render the More Sites page with links to other relevant engineering sites"""
    # Fetch approved external sites grouped by type
    university_clubs = ExternalSite.objects.filter(site_type='university', is_approved=True)
    community_links = ExternalSite.objects.filter(site_type='community', is_approved=True)
    partner_sites = ExternalSite.objects.filter(site_type='partner', is_approved=True)
    
    context = {
        'title': 'Engineering Resources & Links',
        'university_clubs': university_clubs,
        'community_links': community_links,
        'sites': partner_sites
    }
    return render(request, 'core/more_sites.html', context)

def approve_site(request, site_id):
    """Approve a submitted site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to approve sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        site = get_object_or_404(ExternalSite, id=site_id)
        site.is_approved = True
        site.is_rejected = False
        site.save()
        
        messages.success(request, f"Site '{site.name}' has been approved.")
    return redirect('manage_sites')

def reject_site(request, site_id):
    """Reject a submitted site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to reject sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        site = get_object_or_404(ExternalSite, id=site_id)
        site.is_approved = False
        site.is_rejected = True
        site.save()
        
        messages.success(request, f"Site '{site.name}' has been rejected.")
    
    return redirect('manage_sites')


@login_required
def delete_site(request, site_id):
    """Delete a site entirely"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to delete sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        site = get_object_or_404(ExternalSite, id=site_id)
        site_name = site.name
        site.delete()
        
        messages.success(request, f"Site '{site_name}' has been deleted.")
    
    return redirect('manage_sites')

@login_required
def edit_site(request, site_id):
    """Edit an existing site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to edit sites.")
        return redirect('more_sites')
    
    site = get_object_or_404(ExternalSite, id=site_id)
    
    if request.method == 'POST':
        site.name = request.POST.get('name')
        site.url = request.POST.get('url')
        site.description = request.POST.get('description')
        site.site_type = request.POST.get('site_type')
        site.icon = request.POST.get('icon')
        site.save()
        
        messages.success(request, f"Site '{site.name}' has been updated.")
        return redirect('manage_sites')
    
    return render(request, 'core/edit_site.html', {
        'site': site,
        'title': f'Edit Site: {site.name}'
    })

@login_required
def admin_add_site(request):
    """Admin function to directly add a new site"""
    # Check if user has admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to add sites.")
        return redirect('more_sites')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        url = request.POST.get('url')
        description = request.POST.get('description')
        site_type = request.POST.get('site_type')
        icon = request.POST.get('icon')
        
        if name and url and description and site_type:
            # Create the site (automatically approved)
            site = ExternalSite(
                name=name,
                url=url,
                description=description,
                site_type=site_type,
                icon=icon,
                added_by=request.user,
                is_approved=True
            )
            site.save()
            
            messages.success(request, f"Site '{name}' has been added successfully.")
            return redirect('manage_sites')
        else:
            messages.error(request, "Please fill in all required fields.")
            return redirect('manage_sites')
    
    # This should not normally be reached directly
    return redirect('manage_sites')



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
        if form.is_valid():       # Process the form data
            return suggest_resource(request)
    else:
        form = ExternalSiteForm()
    
    return render(request, 'core/site_form.html', {'form': form})


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Product, Review

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if not rating or int(rating) < 1 or int(rating) > 5:
            messages.error(request, "Invalid rating. Please provide a rating between 1 and 5.")
            return redirect('product_detail', slug=product.slug)
        Review.objects.create(product=product, user=request.user, rating=rating, comment=comment)
        messages.success(request, "Your review has been added.")
        return redirect('product_detail', slug=product.slug)
    return redirect('product_detail', slug=product.slug)





# MPWSA
@login_required
def generate_receipt(request, payment_id):
    """Generate a receipt for a payment"""
    # Get the payment or return 404 if not found
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Get membership if it exists
    membership = None
    if hasattr(payment, 'membership'):
        membership = payment.membership
    
    return render(request, 'core/receipt.html', {
        'payment': payment,
        'membership': membership
    })
    
@login_required
def payment_history(request):
    """View user's payment history"""
    # Get all payments for the current user
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'core/payment_history.html', {
        'payments': payments
    })
    

@login_required
def dashboard(request):
    """
    User dashboard showing membership status, recent payments, events, and more
    """
    try:
        # Get the user profile
        if not hasattr(request.user, 'profile'):
            messages.error(request, "You don't have a user profile. Please contact support.")
            return redirect('home')
            
        user_profile = request.user.profile
        
        # Check membership status
        membership_status = user_profile.membership_status
        membership_expiry = user_profile.membership_expiry
        
        # If user is not a member, redirect to membership page with a helpful message
        if membership_status != 'active':
            messages.info(request, "You need to be an active ESA member to access the dashboard. Join us today!")
            return redirect('membership')
        
        # Get recent payments (limit to 3)
        recent_payments = Payment.objects.filter(user=request.user).order_by('-created_at')[:3]
        
        # Get member-get-member payments where current user is the referrer
        mgm_payments = Payment.objects.filter(
            membership__referred_by=request.user
        ).order_by('-created_at')[:3]
        
        # Combine and sort all payments
        all_payments = list(recent_payments) + list(mgm_payments)
        all_payments.sort(key=lambda x: x.created_at, reverse=True)
        recent_payments = all_payments[:3]
        
        # Get user's event registrations (upcoming events)
        upcoming_events = EventRegistration.objects.filter(
            user=user_profile,
            event__start_date__gte=timezone.now().date()
        ).order_by('event__start_date')[:3]
        
        # Get recent orders
        recent_orders = Order.objects.filter(user=user_profile).order_by('-created_at')[:3]
        
        # Get user's blog posts
        recent_posts = BlogPost.objects.filter(
            author=user_profile,
            id__isnull=False  # Ensure we only get posts with valid IDs
        ).order_by('-created_at')[:3]
        
        return render(request, 'core/dashboard.html', {
            'user_profile': user_profile,
            'membership_status': membership_status,
            'membership_expiry': membership_expiry,
            'recent_payments': recent_payments,
            'upcoming_events': upcoming_events,
            'recent_orders': recent_orders,
            'recent_posts': recent_posts,
        })
        
    except Exception as e:
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return redirect('membership')  # Redirect to membership page instead of profile

# Vendor Management Views

@login_required
def vendor_dashboard(request):
    """Dashboard for vendors to manage their products"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Profile not found. Please contact support.")
        return redirect('home')
    
    profile = request.user.profile
    
    # Check if user is a vendor or has store management permissions
    if not (profile.role and profile.role.name == 'Vendor') and not profile.can_manage_store():
        messages.error(request, "You don't have vendor privileges. Contact admin to become a vendor.")
        return redirect('home')
    
    # Get vendor's products
    if profile.is_esa_admin() or profile.can_manage_store():
        # Admin can see all products
        products = Product.objects.all().order_by('-created_at')
    else:
        # Vendor can only see their own products
        products = Product.objects.filter(vendor_user=profile).order_by('-created_at')
    
    # Statistics
    total_products = products.count()
    active_products = products.filter(is_active=True).count()
    pending_approval = products.filter(is_approved=False).count()
    
    context = {
        'title': 'Vendor Dashboard',
        'products': products[:10],  # Show latest 10 products
        'total_products': total_products,
        'active_products': active_products,
        'pending_approval': pending_approval,
        'is_vendor': True,
    }
    
    return render(request, 'core/vendor_dashboard.html', context)

@login_required
def vendor_products(request):
    """List all products for a vendor"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Profile not found.")
        return redirect('home')
    
    profile = request.user.profile
    
    # Check permissions
    if not (profile.role and profile.role.name == 'Vendor') and not profile.can_manage_store():
        messages.error(request, "You don't have vendor privileges.")
        return redirect('home')
    
    # Get products based on user role
    if profile.is_esa_admin() or profile.can_manage_store():
        products = Product.objects.all()
    else:
        products = Product.objects.filter(vendor_user=profile)
    
    # Apply filters
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    if category:
        products = products.filter(category=category)
    
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    elif status == 'pending':
        products = products.filter(is_approved=False)
    elif status == 'approved':
        products = products.filter(is_approved=True)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    products = products.order_by('-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'My Products' if not profile.is_esa_admin() else 'All Products',
        'products': page_obj,
        'categories': Product.CATEGORY_CHOICES,
        'current_category': category,
        'current_status': status,
        'search_query': search,
        'is_vendor': True,
    }
    
    return render(request, 'core/vendor_products.html', context)

@login_required
def manage_vendors(request):
    """Admin view to manage vendors"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_esa_admin():
        messages.error(request, "You don't have permission to manage vendors.")
        return redirect('home')
    
    # Get all users with vendor role or store management permissions
    vendor_profiles = UserProfile.objects.filter(
        Q(role__name='Vendor') | 
        Q(role__name='Store Manager') |
        Q(role__can_post_store_items=True)
    ).select_related('user', 'role').order_by('-created_at')
    
    # Handle POST requests for vendor management
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        try:
            target_user = User.objects.get(id=user_id)
            target_profile = target_user.profile
            
            if action == 'make_vendor':
                vendor_role = UserRole.objects.get(name='Vendor')
                target_profile.role = vendor_role
                target_profile.user_type = 'vendor'
                target_profile.save()
                messages.success(request, f"{target_user.username} is now a vendor.")
                
            elif action == 'remove_vendor':
                # Remove vendor role but don't delete products
                target_profile.role = None
                target_profile.save()
                messages.success(request, f"Vendor privileges removed from {target_user.username}.")
                
        except (User.DoesNotExist, UserRole.DoesNotExist) as e:
            messages.error(request, f"Error: {str(e)}")
        
        return redirect('manage_vendors')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        vendor_profiles = vendor_profiles.filter(
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Get vendor statistics
    vendor_stats = {}
    for profile in vendor_profiles:
        products = Product.objects.filter(vendor_user=profile)
        vendor_stats[profile.id] = {
            'total_products': products.count(),
            'active_products': products.filter(is_active=True).count(),
            'pending_products': products.filter(is_approved=False).count(),
        }
    
    context = {
        'title': 'Manage Vendors',
        'vendor_profiles': vendor_profiles,
        'vendor_stats': vendor_stats,
        'search_query': search,
    }
    
    return render(request, 'core/manage_vendors.html', context)

# Add this at the end of the file, after the manage_vendors function

def payment_coming_soon(request):
    """Temporary page showing that payment functionality is coming soon"""
    return render(request, 'core/payment_coming_soon.html', {
        'title': 'Payment Coming Soon'
    })