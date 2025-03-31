from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string
from decimal import Decimal
from django.urls import reverse
from django.utils.text import slugify

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
        ('other_students', 'Other Students'),
        ('graduate', 'Graduate/Professional'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in months")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.price} KSh"

class Membership(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan_type = models.CharField(max_length=20, choices=MembershipPlan.PLAN_TYPES, default='other_students')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=300)  # Default to other students price
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='mpesa')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_plan_type_display()}"

    def activate(self):
        self.status = 'completed'
        self.is_active = True
        self.start_date = timezone.now()
        self.end_date = self.start_date + timezone.timedelta(days=365)  # 1 year membership
        self.save()

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
            self.membership.status = 'completed'
            self.membership.is_active = True
            self.membership.start_date = timezone.now()
            self.membership.end_date = self.membership.start_date + timezone.timedelta(days=365)  # 1 year membership
            self.membership.save()
            
            # Update user profile
            try:
                profile = self.user.profile
                profile.membership_status = 'active'
                profile.membership_expiry = self.membership.end_date.date()
                profile.save()
            except UserProfile.DoesNotExist:
                pass
        
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
    CATEGORY_CHOICES = [
        ('books', 'Books'),
        ('tools', 'Tools'),
        ('merchandise', 'Merchandise'),
        ('electronics', 'Electronics'),
        ('software', 'Software'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    stock = models.IntegerField(default=0)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    vendor = models.CharField(max_length=100, default='ESA-KU Store', help_text='Company or individual selling the product')
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False, help_text='Feature this product on the store page')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            
            # Ensure slug uniqueness
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = unique_slug
        super().save(*args, **kwargs)

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

class Community(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    logo = models.ImageField(upload_to='communities/logos/', null=True, blank=True)
    banner_image = models.ImageField(upload_to='communities/banners/', null=True, blank=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Communities"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('community_detail', kwargs={'slug': self.slug})

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        ordering = ['-created_at']

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Cart"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart}"
