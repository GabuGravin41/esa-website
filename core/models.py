from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string
from decimal import Decimal

class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('first_year', 'First Year Student'),
        ('student', 'Regular Student'),
        ('graduate', 'Graduate/Professional'),
    ]
    
    MEMBERSHIP_STATUS_CHOICES = [
        ('inactive', 'Inactive'),  # Default state - just created account
        ('active', 'Active'),      # Paid membership
        ('expired', 'Expired'),    # Membership expired
        ('suspended', 'Suspended') # Membership suspended
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    student_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100)
    year_of_study = models.IntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Membership related fields
    membership_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    membership_status = models.CharField(max_length=20, choices=MEMBERSHIP_STATUS_CHOICES, default='inactive')
    membership_expiry = models.DateField(null=True, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')
    
    # Usage limitations for non-members
    blog_posts_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
        
    def is_membership_active(self):
        """Check if user has an active membership"""
        if self.membership_status != 'active':
            return False
        if self.membership_expiry and self.membership_expiry < timezone.now().date():
            self.membership_status = 'expired'
            self.save(update_fields=['membership_status'])
            return False
        return True
    
    def can_comment(self):
        """Check if user can post comments"""
        if self.is_membership_active():
            return True
        return self.comments_count < 5  # Non-members can post max 5 comments
    
    def can_post_blog(self):
        """Check if user can create blog posts"""
        if self.is_membership_active():
            return True
        return False  # Non-members cannot post blogs
    
    def generate_membership_number(self):
        """Generate a unique membership number"""
        if not self.membership_number:
            random_digits = ''.join(random.choices(string.digits, k=5))
            membership_number = f"ESA-KU{random_digits}"
            
            # Check if number already exists
            while UserProfile.objects.filter(membership_number=membership_number).exists():
                random_digits = ''.join(random.choices(string.digits, k=5))
                membership_number = f"ESA-KU{random_digits}"
                
            self.membership_number = membership_number
            self.save(update_fields=['membership_number'])
        
        return self.membership_number

    class Meta:
        ordering = ['-created_at']

class MembershipPlan(models.Model):
    PLAN_TYPES = [
        ('first_year', 'First Year Student'),
        ('student', 'Regular Student'),
        ('graduate', 'Graduate/Professional'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in months")
    features = models.TextField()
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='student')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['price']

class Membership(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='memberships')
    plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.user.username}'s {self.plan.name} Membership"

    def is_active(self):
        return self.status == 'active' and self.end_date > timezone.now()
        
    def activate(self):
        """Activate the membership and update user profile"""
        if self.payment_status and self.status == 'pending':
            self.status = 'active'
            self.save(update_fields=['status'])
            
            # Update UserProfile
            user_profile = self.user
            user_profile.membership_status = 'active'
            user_profile.membership_expiry = self.end_date.date()
            user_profile.user_type = self.plan.plan_type
            
            # Generate membership number if not exists
            if not user_profile.membership_number:
                user_profile.generate_membership_number()
            
            user_profile.save(update_fields=[
                'membership_status', 
                'membership_expiry', 
                'user_type'
            ])
            
            return True
        return False

    class Meta:
        ordering = ['-created_at']

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    membership = models.ForeignKey(Membership, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    
    # For M-Pesa
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    mpesa_receipt = models.CharField(max_length=30, blank=True, null=True)
    
    # For PayPal/Card
    payment_token = models.CharField(max_length=100, blank=True, null=True)
    
    # Common fields
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment #{self.id} - {self.user.username} - {self.amount} {self.currency}"
    
    def complete_payment(self, transaction_id=None):
        """Mark payment as completed and activate membership"""
        if transaction_id:
            self.transaction_id = transaction_id
        
        self.status = 'completed'
        self.save(update_fields=['status', 'transaction_id'])
        
        # If this is a membership payment, activate the membership
        if self.membership:
            self.membership.payment_status = True
            self.membership.save(update_fields=['payment_status'])
            self.membership.activate()
        
        return True
    
    class Meta:
        ordering = ['-payment_date']

# M-Pesa Transaction Model
class MpesaTransaction(models.Model):
    """Model to track M-Pesa transactions"""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='mpesa_transaction')
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    checkout_request_id = models.CharField(max_length=100, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True) 
    mpesa_receipt = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"M-Pesa {self.reference} - {self.status}"
        
    class Meta:
        verbose_name = "M-Pesa Transaction"
        verbose_name_plural = "M-Pesa Transactions"
        ordering = ['-created_at']

# Event Models
class Event(models.Model):
    CATEGORY_CHOICES = [
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('conference', 'Conference'),
        ('social', 'Social Event'),
        ('competition', 'Competition'),
        ('career_fair', 'Career Fair'),
        ('field_trip', 'Field Trip'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    short_description = models.TextField(max_length=200, blank=True, help_text="Short description for previews")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='workshop')
    date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True, help_text="End date for multi-day events")
    location = models.CharField(max_length=200)
    venue_type = models.CharField(max_length=20, choices=[('physical', 'Physical'), ('virtual', 'Virtual'), ('hybrid', 'Hybrid')], default='physical')
    capacity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    featured = models.BooleanField(default=False, help_text="Feature this event on the homepage")
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    speaker = models.CharField(max_length=200, blank=True, help_text="Main speaker or host")
    registration_deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, related_name='created_events', on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def registered_count(self):
        return self.registrations.count()
    
    def seats_left(self):
        registered = self.registered_count()
        return max(0, self.capacity - registered)
    
    def is_registration_open(self):
        if not self.is_active or self.status != 'upcoming':
            return False
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return False
        return self.seats_left() > 0
    
    def is_fully_booked(self):
        return self.seats_left() == 0 and self.capacity > 0

    class Meta:
        ordering = ['date']

class EventRegistration(models.Model):
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('attended', 'Attended'),
        ('cancelled', 'Cancelled'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    payment_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.user.username}'s registration for {self.event.title}"

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-registration_date']

# Store Models
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.user.username}"

    class Meta:
        ordering = ['-order_date']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order #{self.order.id}"

# Blog Models
class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ('research', 'Research Paper'),
        ('journal', 'Journal Article'),
        ('projects', 'Project'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog_images/', null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='journal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class Comment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.author.user.username} on {self.post.title}"

    class Meta:
        ordering = ['-created_at']

# Resource Models
class Resource(models.Model):
    CATEGORY_CHOICES = [
        ('document', 'Document'),
        ('video', 'Video'),
        ('link', 'Link'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    file = models.FileField(upload_to='resources/', null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
