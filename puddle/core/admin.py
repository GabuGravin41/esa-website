from django.contrib import admin
from .models import (
    UserProfile, MembershipPlan, Membership,
    Event, EventRegistration, Product, Order,
    OrderItem, BlogPost, Comment, Resource,
    Contact, Cart, CartItem, UserRole,
    Announcement, NewsletterSubscriber, Partner,
    ExternalSite
)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_admin', 'can_post_events', 'can_post_store_items', 'can_post_resources', 'can_manage_permissions')
    list_filter = ('is_admin', 'can_post_events', 'can_post_store_items', 'can_post_resources')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Permissions', {
            'fields': ('can_post_events', 'can_post_store_items', 'can_post_resources')
        }),
        ('Administrative', {
            'fields': ('is_admin', 'can_manage_permissions'),
            'classes': ('collapse',),
            'description': 'Advanced administrative permissions'
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'department', 'role', 'membership_status', 'display_permissions')
    search_fields = ('user__username', 'user__email', 'student_id', 'department')
    list_filter = ('department', 'year_of_study', 'role', 'membership_status')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'student_id', 'department', 'year_of_study', 'phone_number', 'profile_picture', 'bio')
        }),
        ('Membership', {
            'fields': ('membership_number', 'membership_status', 'membership_expiry', 'user_type')
        }),
        ('Roles & Permissions', {
            'fields': ('role', 'custom_permissions', 'can_post_events', 'can_post_store_items', 'can_post_resources')
        }),
        ('Usage Counters', {
            'fields': ('blog_posts_count', 'comments_count'),
            'classes': ('collapse',)
        }),
    )
    
    def display_permissions(self, obj):
        permissions = []
        if obj.role and obj.role.is_admin:
            return "Admin (All Permissions)"
        
        if obj.can_manage_events() or (obj.role and obj.role.can_post_events):
            permissions.append("Events")
        if obj.can_manage_store() or (obj.role and obj.role.can_post_store_items):
            permissions.append("Store")
        if obj.can_manage_resources() or (obj.role and obj.role.can_post_resources):
            permissions.append("Resources")
            
        if not permissions:
            return "No special permissions"
        return ", ".join(permissions)
    
    display_permissions.short_description = "Permissions"

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'subject', 'message']

@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'duration', 'is_active']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name']

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan_type', 'amount', 'payment_method', 'status', 'is_active']
    list_filter = ['status', 'is_active', 'plan_type']
    search_fields = ['user__username', 'user__email']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'location', 'capacity', 'price', 'status', 'is_active')
    search_fields = ('title', 'description', 'location')
    list_filter = ('status', 'is_active', 'category', 'event_type')
    date_hierarchy = 'start_date'

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'registration_date', 'status', 'payment_status')
    search_fields = ('event__title', 'user__user__username')
    list_filter = ('status', 'payment_status')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'is_active']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'order_date', 'total_amount', 'status', 'payment_status')
    search_fields = ('user__user__username',)
    list_filter = ('status', 'payment_status')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    search_fields = ('order__user__user__username', 'product__name')

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'is_published')
    search_fields = ('title', 'content', 'author__user__username')
    list_filter = ('is_published', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('content', 'created_by', 'created_at')
    search_fields = ('content', 'created_by__username')
    list_filter = ('created_at',)

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'uploaded_by', 'created_at', 'is_approved')
    search_fields = ('title', 'description', 'uploaded_by__user__username')
    list_filter = ('category', 'created_at', 'is_approved')
    actions = ['approve_resources', 'reject_resources']
    
    def approve_resources(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} resources have been approved.')
    approve_resources.short_description = "Approve selected resources"
    
    def reject_resources(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} resources have been rejected.')
    reject_resources.short_description = "Reject selected resources"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__username']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']
    list_filter = ['created_at']
    search_fields = ['cart__user__username', 'product__name']

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at', 'expiry_date')
    list_filter = ('is_active',)
    search_fields = ('title', 'content')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    date_hierarchy = 'subscribed_at'
    ordering = ('-subscribed_at',)

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    date_hierarchy = 'created_at'
    ordering = ('name',)

@admin.register(ExternalSite)
class ExternalSiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'site_type', 'url', 'is_approved', 'is_rejected', 'added_by', 'created_at')
    list_filter = ('site_type', 'is_approved', 'is_rejected')
    search_fields = ('name', 'description')
    actions = ['approve_sites', 'unapprove_sites', 'reject_sites', 'unreject_sites']
    date_hierarchy = 'created_at'
    fieldsets = (
        (None, {
            'fields': ('name', 'url', 'description', 'site_type')
        }),
        ('Appearance', {
            'fields': ('logo', 'icon')
        }),
        ('Management', {
            'fields': ('added_by', 'is_approved')
        }),
    )
    
    def approve_sites(self, request, queryset):
        updated = queryset.update(is_approved=True, is_rejected=False)
        self.message_user(request, f"{updated} sites were successfully approved.")
    
    def reject_sites(self, request, queryset):
        updated = queryset.update(is_rejected=True, is_approved=False)
        self.message_user(request, f"{updated} sites were successfully rejected.")
        
    def unreject_sites(self, request, queryset):
        updated = queryset.update(is_rejected=False)
        self.message_user(request, f"{updated} sites were removed from the rejected list.")
        self.message_user(request, f'{updated} sites have been approved.')
    approve_sites.short_description = "Approve selected sites"
    
    def unapprove_sites(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} sites have been unapproved.')
    unapprove_sites.short_description = "Unapprove selected sites"
