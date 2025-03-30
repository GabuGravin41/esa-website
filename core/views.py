from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import datetime
import json
import uuid
from decimal import Decimal

from .models import (
    Event, EventRegistration, Product, Order,
    OrderItem, BlogPost, Comment, Resource,
    MembershipPlan, Membership, UserProfile,
    Payment, MpesaTransaction
)
from .forms import (
    EventForm, EventRegistrationForm,
    ProductForm, OrderForm, OrderItemForm,
    BlogPostForm, CommentForm, ResourceForm,
    MembershipPaymentForm, MpesaPaymentForm
)
from .services import MpesaService, PayPalService

def home(request):
    events = Event.objects.filter(is_active=True)[:3]
    blog_posts = BlogPost.objects.filter(is_published=True)[:3]
    context = {
        'events': events,
        'blog_posts': blog_posts,
    }
    return render(request, 'core/home.html', context)

def about(request):
    return render(request, 'core/about.html')

def membership(request):
    plans = MembershipPlan.objects.filter(is_active=True)
    
    # Get user type if authenticated
    user_type = None
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            user_type = profile.user_type
            is_member = profile.is_membership_active()
        except UserProfile.DoesNotExist:
            is_member = False
    else:
        is_member = False
    
    context = {
        'plans': plans,
        'user_type': user_type,
        'is_member': is_member
    }
    return render(request, 'core/membership.html', context)

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
            description = f"ESA-KU Membership Payment: {payment.membership.plan.name}"
            
            # Update payment with phone number
            payment.phone_number = phone_number
            payment.save(update_fields=['phone_number'])
            
            # Create M-Pesa transaction record
            mpesa_tx = MpesaTransaction.objects.create(
                payment=payment,
                phone_number=phone_number,
                amount=amount,
                reference=reference,
                description=description,
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
        'membership': payment.membership,
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
    
    messages.info(request, 'Payment was cancelled. Your membership has not been activated.')
    return redirect('membership')

@login_required
def payment_status(request, payment_id):
    """Check payment status"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
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
                mpesa_tx.transaction_id = response.get('MpesaReceiptNumber')
                mpesa_tx.save(update_fields=['status', 'transaction_id'])
                
                # Complete payment and activate membership
                payment.complete_payment(mpesa_tx.transaction_id)
                
                messages.success(request, 'Payment completed successfully! Your membership is now active.')
                return redirect('dashboard')
    
    return render(request, 'core/payment_status.html', {
        'payment': payment,
        'membership': payment.membership
    })

@csrf_exempt
@require_POST
def mpesa_callback(request):
    """Handle M-Pesa callback from Safaricom"""
    try:
        # Parse the callback JSON
        data = json.loads(request.body)
        body = data.get('Body', {})
        callback_data = body.get('stkCallback', {})
        
        # Extract important details
        checkout_request_id = callback_data.get('CheckoutRequestID')
        result_code = callback_data.get('ResultCode')
        result_desc = callback_data.get('ResultDesc')
        
        # Find the transaction
        try:
            mpesa_tx = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
            
            if result_code == 0:  # Success
                # Extract transaction details
                items = callback_data.get('CallbackMetadata', {}).get('Item', [])
                receipt_number = next((item['Value'] for item in items if item['Name'] == 'MpesaReceiptNumber'), None)
                
                # Update transaction
                mpesa_tx.status = 'completed'
                mpesa_tx.transaction_id = receipt_number
                mpesa_tx.mpesa_receipt = receipt_number
                mpesa_tx.save(update_fields=['status', 'transaction_id', 'mpesa_receipt'])
                
                # Complete payment and activate membership
                payment = mpesa_tx.payment
                payment.complete_payment(receipt_number)
            else:
                # Payment failed
                mpesa_tx.status = 'failed'
                mpesa_tx.save(update_fields=['status'])
                
                # Mark payment as failed
                payment = mpesa_tx.payment
                payment.status = 'failed'
                payment.notes = f"Failed: {result_desc}"
                payment.save(update_fields=['status', 'notes'])
            
            return JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Callback processed successfully"
            })
        except MpesaTransaction.DoesNotExist:
            return JsonResponse({
                "ResultCode": 1,
                "ResultDesc": "Transaction not found"
            })
    except Exception as e:
        return JsonResponse({
            "ResultCode": 1,
            "ResultDesc": f"Error processing callback: {str(e)}"
        })

def events(request):
    # Get filter parameters from URL
    category = request.GET.get('category')
    date_filter = request.GET.get('date')
    location = request.GET.get('location')
    search = request.GET.get('search')
    
    # Base queryset - get active events
    events_list = Event.objects.filter(is_active=True)
    
    # Apply category filter
    if category and category != 'all':
        events_list = events_list.filter(category=category)
    
    # Apply date filter
    if date_filter:
        today = timezone.now().date()
        if date_filter == 'today':
            events_list = events_list.filter(date__date=today)
        elif date_filter == 'this_week':
            week_start = today - timezone.timedelta(days=today.weekday())
            week_end = week_start + timezone.timedelta(days=6)
            events_list = events_list.filter(date__date__range=[week_start, week_end])
        elif date_filter == 'this_month':
            events_list = events_list.filter(date__year=today.year, date__month=today.month)
        elif date_filter == 'next_month':
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year
            events_list = events_list.filter(date__year=next_year, date__month=next_month)
    
    # Apply location filter
    if location and location != 'all':
        events_list = events_list.filter(location__icontains=location)
    
    # Apply search filter
    if search:
        events_list = events_list.filter(
            models.Q(title__icontains=search) | 
            models.Q(description__icontains=search) |
            models.Q(speaker__icontains=search)
        )
    
    # Get category choices for the filter
    categories = [choice[0] for choice in Event.CATEGORY_CHOICES]
    
    # Split events into featured, upcoming, and past
    featured_event = events_list.filter(featured=True, status='upcoming').order_by('date').first()
    
    # Remove featured event from other lists
    if featured_event:
        upcoming_events = events_list.filter(status='upcoming').exclude(id=featured_event.id).order_by('date')
    else:
        upcoming_events = events_list.filter(status='upcoming').order_by('date')
    
    past_events = events_list.filter(status='completed').order_by('-date')[:3]
    
    # Get unique locations for the filter dropdown
    all_locations = Event.objects.values_list('location', flat=True).distinct()
    
    context = {
        'featured_event': featured_event,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'categories': categories,
        'category': category,
        'date_filter': date_filter,
        'location': location,
        'search': search,
        'all_locations': all_locations,
    }
    return render(request, 'core/events.html', context)

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if the user is already registered
    registration = None
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            registration = EventRegistration.objects.filter(event=event, user=user_profile).first()
        except UserProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        form = EventRegistrationForm(request.POST)
        if form.is_valid():
            if request.user.is_authenticated:
                try:
                    # Get user profile
                    user_profile = UserProfile.objects.get(user=request.user)
                    
                    # Check if the event is fully booked
                    if event.is_fully_booked():
                        messages.error(request, 'Sorry, this event is fully booked.')
                    elif event.status != 'upcoming':
                        messages.error(request, 'Registration for this event is closed.')
                    else:
                        # Create the registration
                        registration = EventRegistration(
                            event=event,
                            user=user_profile,
                            status='registered',
                            payment_status=event.price <= 0  # Auto-complete payment if free
                        )
                        registration.save()
                        messages.success(request, 'Successfully registered for the event!')
                except UserProfile.DoesNotExist:
                    messages.error(request, 'Please complete your profile before registering.')
            else:
                # For demo purposes, use a default user
                default_user, created = User.objects.get_or_create(
                    username='default_event_attendee',
                    defaults={'email': 'attendee@example.com'}
                )
                # Get or create a default profile for the user
                default_profile, created = UserProfile.objects.get_or_create(
                    user=default_user,
                    defaults={
                        'student_id': 'EVENT001',
                        'department': 'Event Department',
                        'year_of_study': 1,
                        'bio': 'Default attendee profile',
                        'phone_number': ''
                    }
                )
                # Create the registration
                registration = EventRegistration(
                    event=event,
                    user=default_profile,
                    status='registered',
                    payment_status=event.price <= 0  # Auto-complete payment if free
                )
                registration.save()
                messages.success(request, 'Successfully registered for the event! (Demo mode)')
            
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventRegistrationForm()

    # Get related events (same category)
    related_events = Event.objects.filter(
        category=event.category, 
        is_active=True,
        status='upcoming'
    ).exclude(id=event.id).order_by('date')[:3]

    context = {
        'event': event,
        'registration': registration,
        'form': form,
        'related_events': related_events,
    }
    return render(request, 'core/event_detail.html', context)

def store(request):
    products = Product.objects.filter(is_active=True)
    context = {
        'products': products,
    }
    return render(request, 'core/store.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        # Placeholder for authentication - will be implemented later
        # For now, just show success message
        messages.success(request, f'{product.name} added to cart!')
        return redirect('store')
    
    return render(request, 'core/product_detail.html', {'product': product})

def cart(request):
    # Placeholder data for cart
    order = None
    order_items = []
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'core/cart.html', context)

def checkout(request):
    # Placeholder data for checkout
    order = None
    order_items = []
    
    if request.method == 'POST':
        # Placeholder for checkout process
        messages.success(request, 'Order placed successfully!')
        return redirect('home')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'core/checkout.html', context)

def blog(request):
    # Get filter parameters from URL
    category = request.GET.get('category')
    sort = request.GET.get('sort', 'latest')
    search = request.GET.get('search')
    
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
        
        # Apply sorting
        if sort == 'latest':
            posts = posts.order_by('-created_at')
        elif sort == 'popular':
            # Placeholder for popular sorting - would normally count views or interactions
            # For now, just randomize as an example
            posts = posts.order_by('?')
        elif sort == 'trending':
            # Placeholder for trending - would normally be based on recent engagement
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
    
    context = {
        'posts': posts,
        'recent_posts': recent_posts,
        'category': category,
        'sort': sort,
        'search': search,
        'categories': categories,
        'category_counts': category_counts,
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
    return render(request, 'core/blog_post_detail.html', context)

def resources(request):
    resources_list = Resource.objects.all()
    context = {
        'resources': resources_list,
    }
    return render(request, 'core/resources.html', context)

@login_required
def blog_post_create(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            # In a real implementation, this would use the authenticated user
            # For development, we'll use a default user
            default_user, created = User.objects.get_or_create(
                username='default_author',
                defaults={'email': 'default@example.com'}
            )
            # Get or create a default profile for the user
            default_profile, created = UserProfile.objects.get_or_create(
                user=default_user,
                defaults={
                    'student_id': 'DEFAULT001',
                    'department': 'Default Department',
                    'year_of_study': 1,
                    'bio': 'Default author profile',
                    'phone_number': ''
                }
            )
            
            # Save the blog post with the default author
            blog_post = form.save(commit=False)
            blog_post.author = default_profile
            blog_post.save()
            
            messages.success(request, 'Blog post created successfully!')
            return redirect('blog_post_detail', post_id=blog_post.id)
    else:
        form = BlogPostForm()
    
    return render(request, 'core/blog_post_form.html', {'form': form, 'is_create': True})

@login_required
def blog_post_edit(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    
    # Check if user is authorized to edit this post
    # For development, we skip this check
    # if post.author.user != request.user:
    #     messages.error(request, "You don't have permission to edit this post")
    #     return redirect('blog_post_detail', post_id=post.id)
    
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            # Save the changes
            form.save()
            messages.success(request, 'Blog post updated successfully!')
            return redirect('blog_post_detail', post_id=post.id)
    else:
        form = BlogPostForm(instance=post)
    
    return render(request, 'core/blog_post_form.html', {'form': form, 'is_create': False, 'post': post})

@login_required
def blog_post_delete(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    
    # Check if user is authorized to delete this post
    # For development, we skip this check
    # if post.author.user != request.user:
    #     messages.error(request, "You don't have permission to delete this post")
    #     return redirect('blog_post_detail', post_id=post.id)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Blog post deleted successfully!')
        return redirect('blog')
    
    return render(request, 'core/blog_post_confirm_delete.html', {'post': post})

@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save()
            messages.success(request, 'Event created successfully!')
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    
    return render(request, 'core/event_form.html', {'form': form, 'is_create': True})

@login_required
def event_edit(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'core/event_form.html', {'form': form, 'is_create': False, 'event': event})

@login_required
def event_delete(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully!')
        return redirect('events')
    
    return render(request, 'core/event_confirm_delete.html', {'event': event})

@login_required
def event_register(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if the user is already registered
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        existing_registration = EventRegistration.objects.filter(event=event, user=user_profile).exists()
        
        if existing_registration:
            messages.info(request, 'You are already registered for this event.')
        else:
            # Check if the event is fully booked
            if event.is_fully_booked():
                messages.error(request, 'Sorry, this event is fully booked.')
            elif event.status != 'upcoming':
                messages.error(request, 'Registration for this event is closed.')
            else:
                # Create the registration
                registration = EventRegistration(
                    event=event,
                    user=user_profile,
                    status='registered',
                    payment_status=event.price <= 0  # Auto-complete payment if free
                )
                registration.save()
                messages.success(request, 'Successfully registered for the event!')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Please complete your profile before registering.')
    
    return redirect('event_detail', event_id=event.id)

@login_required
def event_cancel_registration(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        registration = EventRegistration.objects.get(event=event, user=user_profile)
        registration.status = 'cancelled'
        registration.save()
        messages.success(request, 'Your registration has been cancelled.')
    except (UserProfile.DoesNotExist, EventRegistration.DoesNotExist):
        messages.error(request, 'Registration not found.')
    
    return redirect('event_detail', event_id=event.id)
