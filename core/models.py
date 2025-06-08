from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string
from decimal import Decimal
from django.urls import reverse
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from threading import current_thread

import requests
import base64
from datetime import datetime
import json

from django.contrib.auth.models import User



# Admin credentials (hardcoded for security purposes)
ADMIN_CREDENTIALS = [
    {
        'username': 'admin',
        'email': 'admin@example.com',
        'password': 'adminpassword123',
        'first_name': 'System',
        'last_name': 'Admin'
    },
    {
        'username': 'moderator',
        'email': 'moderator@example.com',
        'password': 'moderatorpassword123',
        'first_name': 'Content',
        'last_name': 'Moderator'
    }
]

def get_default_user():
    # Use this function to set a default user when needed
    try:
        return User.objects.get(username='admin')
    except User.DoesNotExist:
        # Create an admin user if one doesn't exist
        admin_data = ADMIN_CREDENTIALS[0]
        user = User.objects.create_user(
            username=admin_data['username'],
            email=admin_data['email'],
            password=admin_data['password'],
            first_name=admin_data['first_name'],
            last_name=admin_data['last_name']
        )
        return user

def initialize_admin_users():
    """Create default admin users if they don't exist"""
    # Create admin role if it doesn't exist
    admin_role, created = UserRole.objects.get_or_create(
        name='System Admin',
        defaults={
            'description': 'Full system administrator with all permissions',
            'is_admin': True,
            'can_post_events': True,
            'can_post_store_items': True,
            'can_post_resources': True,
            'can_manage_permissions': True
        }
    )
    
    moderator_role, created = UserRole.objects.get_or_create(
        name='Content Moderator',
        defaults={
            'description': 'Can moderate site content',
            'is_admin': False,
            'can_post_events': True,
            'can_post_store_items': True,
            'can_post_resources': True,
            'can_manage_permissions': False
        }
    )
    
    # Create admin users
    for admin_data in ADMIN_CREDENTIALS:
        user, created = User.objects.get_or_create(
            username=admin_data['username'],
            defaults={
                'email': admin_data['email'],
                'first_name': admin_data['first_name'],
                'last_name': admin_data['last_name'],
                'is_staff': True,  # Can access Django admin
                'is_active': True
            }
        )
        
        if created:
            user.set_password(admin_data['password'])
            user.save()
            
        # Get or update user profile
        try:
            profile = UserProfile.objects.get(user=user)
            # Update profile with admin details if it exists
            profile.student_id = f"ADMIN{user.id:03d}"
            profile.department = "Administration"
            profile.year_of_study = 0
            profile.membership_status = "active"
            profile.membership_expiry = timezone.now().date().replace(year=timezone.now().year + 10)
            profile.user_type = "staff"
            profile.custom_permissions = True
        except UserProfile.DoesNotExist:
            # Only create if it doesn't exist (which should not happen due to the signal)
            profile = UserProfile.objects.create(
                user=user,
                student_id=f"ADMIN{user.id:03d}",
                department="Administration",
                year_of_study=0,
                phone_number="",
                membership_status="active",
                membership_expiry=timezone.now().date().replace(year=timezone.now().year + 10),
                user_type="staff",
                custom_permissions=True
            )
        
        # Set appropriate role
        if user.username == 'admin':
            profile.role = admin_role
        elif user.username == 'moderator':
            profile.role = moderator_role
            
        profile.save()

# Rest of your model classes
class UserRole(models.Model):
    """Model to define user roles and permissions"""
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    
    # Permission flags
    can_post_events = models.BooleanField(default=False, help_text="Can create and manage events")
    can_post_store_items = models.BooleanField(default=False, help_text="Can add products to the store")
    can_post_resources = models.BooleanField(default=False, help_text="Can upload resources")
    
    # Admin permissions
    is_admin = models.BooleanField(default=False, help_text="Has full admin access")
    can_manage_permissions = models.BooleanField(default=False, help_text="Can manage other users' permissions")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

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
    
    # Role and permissions
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles")
    
    # Individual permission overrides (override role permissions)
    custom_permissions = models.BooleanField(default=False, help_text="If enabled, individual permissions override role permissions")
    can_post_events = models.BooleanField(default=False)
    can_post_store_items = models.BooleanField(default=False)
    can_post_resources = models.BooleanField(default=False)
    
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
    
    def has_permission(self, permission_name):
        """Generic method to check if user has a specific permission"""
        # Check if user is a superuser or ESA admin
        if self.user.is_superuser or (self.role and self.role.is_admin):
            return True
            
        # Use custom permissions if enabled, otherwise use role permissions
        if self.custom_permissions:
            return getattr(self, permission_name, False)
        elif self.role:
            return getattr(self.role, permission_name, False)
        return False
    
    def can_manage_events(self):
        """Check if user can create and manage events"""
        return self.has_permission('can_post_events')
    
    def can_manage_store(self):
        """Check if user can add and manage store products"""
        return self.has_permission('can_post_store_items')
    
    def can_manage_resources(self):
        """Check if user can upload and manage resources"""
        return self.has_permission('can_post_resources')
    
    def is_esa_admin(self):
        """Check if user has ESA admin privileges"""
        return self.role and self.role.is_admin
    
    def can_manage_permissions(self):
        """Check if user can manage permissions"""
        if self.user.is_superuser:
            return True
        return self.role and self.role.can_manage_permissions
    
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
    referred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='referrals')

    def __str__(self):
        return f"{self.user.username} - {self.get_plan_type_display()}"

    def activate(self):
        self.status = 'completed'
        self.is_active = True
        self.start_date = timezone.now()
        self.end_date = self.start_date + timezone.timedelta(days=365)  # 1 year membership
        self.save()




# Event Models
class Comment(models.Model):
    """Model for comments on both blog posts and discussions"""
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional fields for different types of comments
    post = models.ForeignKey('BlogPost', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    discussion = models.ForeignKey('Discussion', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.created_by.username}"

class Event(models.Model):
    """Consolidated Event model for both standalone and community events"""
    CATEGORY_CHOICES = [
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('conference', 'Conference'),
        ('networking', 'Networking'),
        ('competition', 'Competition'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    EVENT_TYPE_CHOICES = [
        ('physical', 'Physical'),
        ('virtual', 'Virtual'),
        ('hybrid', 'Hybrid'),
    ]
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    short_description = models.TextField(max_length=200, blank=True, help_text="Short description for previews")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES, default='physical')
    
    # Date and time fields
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(default='09:00:00')
    end_time = models.TimeField(default='17:00:00')
    registration_deadline = models.DateTimeField(null=True, blank=True)
    
    # Location fields
    location = models.CharField(max_length=255)
    is_online = models.BooleanField(default=False)
    online_link = models.URLField(blank=True, null=True)
    
    # Event details
    capacity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    featured = models.BooleanField(default=False, help_text="Feature this event on the homepage")
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    speaker = models.CharField(max_length=200, blank=True, help_text="Main speaker or host")
    
    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_active = models.BooleanField(default=True)
    
    # Relationships
    community = models.ForeignKey('Community', on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'slug': self.slug})

    @property
    def registered_count(self):
        return self.registrations.filter(status='registered').count()

    @property
    def seats_left(self):
        return self.capacity - self.registered_count

    def is_registration_open(self):
        if self.registration_deadline:
            return timezone.now() <= self.registration_deadline
        return True

    def is_fully_booked(self):
        return self.registered_count >= self.capacity

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['start_date']

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
        ('general', 'General'),
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('books', 'Books'),
        ('home', 'Home & Garden'),
        ('sports', 'Sports & Outdoors'),
        ('automotive', 'Automotive'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ('-created_at',)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

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
        ('thesis', 'Thesis'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='blog_images/', null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='journal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class Community(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General Engineering'),
        ('mechanical', 'Mechanical Engineering'),
        ('electrical', 'Electrical Engineering'),
        ('civil', 'Civil Engineering'),
        ('computer', 'Computer Engineering'),
        ('aerospace', 'Aerospace Engineering'),
        ('chemical', 'Chemical Engineering'),
        ('biomedical', 'Biomedical Engineering'),
        ('environmental', 'Environmental Engineering'),
        ('industrial', 'Industrial Engineering'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    image = models.ImageField(upload_to='community_images', blank=True, null=True)
    rules = models.TextField(blank=True, null=True)
    is_private = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_communities', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Communities'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('community_detail', kwargs={'slug': self.slug})
    
    @property
    def member_count(self):
        return self.members.count()

class CommunityMember(models.Model):
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    ]
    
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('community', 'user')
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.community.name} ({self.get_role_display()})"

# Discussion models for communities
class Discussion(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='discussions')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('discussion_detail', kwargs={'community_slug': self.community.slug, 'slug': self.slug})
    
    @property
    def comment_count(self):
        return self.comments.count()

class EventAttendee(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events_attending')
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('event', 'user')
    
    def __str__(self):
        return f"{self.user.username} attending {self.event.title}"

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

class Resource(models.Model):
    CATEGORY_CHOICES = [
        ('document', 'Document'),
        ('video', 'Video'),
        ('link', 'Link'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='document')
    file = models.FileField(upload_to='resources/', null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    thumbnail = models.ImageField(upload_to='resource_thumbnails/', null=True, blank=True)
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='uploaded_resources', null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    tags = models.ManyToManyField('ResourceTag', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('resource_detail', kwargs={'pk': self.pk})

    def increment_download_count(self):
        self.download_count += 1
        self.save(update_fields=['download_count'])

    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def clean(self):
        if not self.file and not self.link:
            raise ValidationError('Either a file or a link must be provided.')
        if self.file and self.link:
            raise ValidationError('Cannot have both a file and a link.')

class ResourceTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ExternalSite(models.Model):
    SITE_TYPE_CHOICES = [
        ('university', 'University Club'),
        ('community', 'Community Resource'),
        ('partner', 'Official Partner'),
    ]
    
    name = models.CharField(max_length=255)
    url = models.URLField()
    description = models.TextField()
    site_type = models.CharField(max_length=20, choices=SITE_TYPE_CHOICES)
    logo = models.ImageField(upload_to='site_logos/', null=True, blank=True)
    icon = models.CharField(max_length=50, null=True, blank=True, help_text="FontAwesome icon class (e.g., 'fas fa-users')")
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='suggested_sites')
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['site_type', 'name']
        verbose_name = 'External Site'
        verbose_name_plural = 'External Sites'
    
    def __str__(self):
        return f"{self.name} ({self.get_site_type_display()})"

# Signal to initialize admin users and create default profiles if needed
@receiver(post_save, sender=User, dispatch_uid="core_create_user_profile")
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Only create a profile if one doesn't already exist
        # and we're not coming from the registration form (which has its own signal)
        thread = current_thread()
        from_registration = getattr(thread, 'student_id', None) is not None
        
        # Skip this handler if we're coming from the registration form
        # Let the accounts app handler handle the profile creation with the student's ID
        if from_registration:
            return
            
        # This is for admin-created users or system-created users
        # Not for regular user registration
        if not hasattr(instance, 'profile'):
            # For admin users only - must be manually set for regular users
            if instance.is_staff or instance.is_superuser:
                student_id = f"ADMIN{instance.id:03d}"
                    
                try:
                    # Create profile with a unique student_id for admin users
                    UserProfile.objects.create(
                        user=instance,
                        student_id=student_id,
                        department="Administration",
                        year_of_study=0
                    )
                except Exception as e:
                    # Log any errors but don't crash
                    print(f"Error creating profile from core signal for user {instance}: {e}")
        
        # Initialize admin users if this is the first user being created
        if User.objects.count() == 1:
            initialize_admin_users()

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return self.expiry_date and self.expiry_date < timezone.now()

    def __str__(self):
        return self.title

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Partner(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='partner_logos/')
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

       





from django.core.exceptions import ValidationError

def validate_phone_number(phone):
    """Validate M-Pesa phone number format"""
    if not isinstance(phone, str):
        raise ValidationError('Phone number must be a string')
    
    phone = phone.strip()
    if not phone:
        raise ValidationError('Phone number cannot be empty')
        
    if not phone.startswith('254'):
        raise ValidationError('Phone number must start with 254')
        
    if len(phone) != 12:
        raise ValidationError('Phone number must be 12 digits')
        
    if not phone.isdigit():
        raise ValidationError('Phone number must contain only digits')
        
    # Check if starts with valid prefix after 254 (7 or 1)
    if not phone[3] in ['7', '1']:
        raise ValidationError('Phone number must start with 254 followed by 7 or 1')
        
    return phone

def validate_mpesa_amount(amount):
    """Validate M-Pesa amount"""
    if amount is None:
        raise ValidationError('Amount cannot be None')
        
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValidationError('Amount must be a number')
        
    if amount <= 0:
        raise ValidationError('Amount must be greater than 0')
        
    if amount > 150000:
        raise ValidationError('Amount cannot exceed KES 150,000')
        
    if not float(amount).is_integer():
        raise ValidationError('Amount must be a whole number')
        
    return int(amount)

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=1, help_text="Rating between 1 and 5")
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

    class Meta:
        ordering = ['-created_at']
        


class Payment(models.Model):
    """Base payment model"""
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('card', 'Credit/Debit Card'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'), 
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.user.username} - {self.amount} {self.currency}"

    def complete_payment(self, transaction_id=None):
        """Mark payment as completed"""
        if transaction_id:
            self.transaction_id = transaction_id
        self.status = 'completed'
        self.save()
        return True

    class Meta:
        ordering = ['-created_at']

class MpesaTransaction(models.Model):
    """M-Pesa specific transaction details"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'), 
        ('failed', 'Failed'),
    ]

    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='mpesa_transaction')
    phone_number = models.CharField(max_length=15, validators=[validate_phone_number])
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[validate_mpesa_amount])
    checkout_request_id = models.CharField(max_length=100, null=True, blank=True)
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    mpesa_receipt = models.CharField(max_length=30, null=True, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result_code = models.CharField(max_length=5, null=True, blank=True)
    result_description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"M-Pesa Transaction - {self.payment.id} - {self.status}"

    def complete_transaction(self, mpesa_receipt, transaction_date=None):
        """Mark transaction as completed and update payment"""
        self.status = 'completed'
        self.mpesa_receipt = mpesa_receipt
        if transaction_date:
            self.transaction_date = transaction_date
        self.save()
        
        # Update associated payment
        self.payment.complete_payment(transaction_id=mpesa_receipt)
        return True

    class Meta:
        verbose_name = "M-Pesa Transaction"
        verbose_name_plural = "M-Pesa Transactions"
        ordering = ['-created_at']