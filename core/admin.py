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
    list_display = ('user_full_name', 'student_id', 'membership_number', 'department', 'year_of_study', 
                   'membership_status', 'membership_expiry', 'phone_number', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 
                    'student_id', 'membership_number', 'department', 'phone_number')
    list_filter = ('department', 'year_of_study', 'membership_status', 'user_type', 'created_at')
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'student_id', 'phone_number', 'profile_picture', 'bio')
        }),
        ('Academic Information', {
            'fields': ('department', 'course', 'year_of_study', 'user_type')
        }),
        ('Membership', {
            'fields': ('membership_number', 'membership_status', 'membership_expiry')
        }),
        ('Roles & Permissions', {
            'fields': ('role', 'custom_permissions', 'can_post_events', 'can_post_store_items', 'can_post_resources'),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('blog_posts_count', 'comments_count'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def user_full_name(self, obj):
        full_name = obj.user.get_full_name()
        return full_name if full_name else obj.user.username
    user_full_name.short_description = "Full Name"
    user_full_name.admin_order_field = 'user__first_name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'role')
    
    actions = ['activate_membership', 'deactivate_membership', 'export_members']
    
    def activate_membership(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        for profile in queryset:
            profile.membership_status = 'active'
            if not profile.membership_expiry:
                profile.membership_expiry = timezone.now().date() + timedelta(days=365)
            profile.save()
        
        self.message_user(request, f"Successfully activated membership for {queryset.count()} users.")
    activate_membership.short_description = "Activate membership for selected users"
    
    def deactivate_membership(self, request, queryset):
        queryset.update(membership_status='inactive')
        self.message_user(request, f"Successfully deactivated membership for {queryset.count()} users.")
    deactivate_membership.short_description = "Deactivate membership for selected users"
    
    def export_members(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="esa_members.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Full Name', 'Username', 'Email', 'Student ID', 'Member Number', 
                        'Department', 'Course', 'Year', 'Phone', 'Membership Status', 
                        'Membership Expiry', 'Join Date'])
        
        for profile in queryset:
            writer.writerow([
                profile.user.get_full_name(),
                profile.user.username,
                profile.user.email,
                profile.student_id,
                profile.membership_number or 'N/A',
                profile.department,
                profile.course or 'N/A',
                profile.get_year_of_study_display() if profile.year_of_study else 'N/A',
                profile.phone_number,
                profile.get_membership_status_display(),
                profile.membership_expiry or 'N/A',
                profile.created_at.date()
            ])
        
        return response
    export_members.short_description = "Export selected members to CSV"

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
    list_display = ('user_full_name', 'membership_number', 'plan_type', 'amount', 'payment_method', 
                   'status', 'is_active', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'is_active', 'plan_type', 'payment_method', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 
                    'membership_number')
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Member Information', {
            'fields': ('user', 'membership_number', 'plan_type')
        }),
        ('Payment Details', {
            'fields': ('amount', 'payment_method', 'payment', 'status')
        }),
        ('Membership Period', {
            'fields': ('is_active', 'start_date', 'end_date')
        }),
        ('Referral', {
            'fields': ('referred_by',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def user_full_name(self, obj):
        full_name = obj.user.get_full_name()
        return full_name if full_name else obj.user.username
    user_full_name.short_description = "Member Name"
    user_full_name.admin_order_field = 'user__first_name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'payment')
    
    actions = ['activate_memberships', 'deactivate_memberships', 'export_memberships']
    
    def activate_memberships(self, request, queryset):
        from django.utils import timezone
        
        for membership in queryset:
            membership.activate()
            # Also update user profile
            try:
                profile = membership.user.profile
                profile.membership_status = 'active'
                profile.membership_expiry = membership.end_date.date() if membership.end_date else None
                profile.save()
            except:
                pass
        
        self.message_user(request, f"Successfully activated {queryset.count()} memberships.")
    activate_memberships.short_description = "Activate selected memberships"
    
    def deactivate_memberships(self, request, queryset):
        queryset.update(is_active=False, status='cancelled')
        
        # Update user profiles
        for membership in queryset:
            try:
                profile = membership.user.profile
                profile.membership_status = 'inactive'
                profile.save()
            except:
                pass
        
        self.message_user(request, f"Successfully deactivated {queryset.count()} memberships.")
    deactivate_memberships.short_description = "Deactivate selected memberships"
    
    def export_memberships(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="esa_memberships.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Member Name', 'Username', 'Email', 'Member Number', 'Plan Type', 
                        'Amount', 'Payment Method', 'Status', 'Active', 'Start Date', 
                        'End Date', 'Join Date'])
        
        for membership in queryset:
            writer.writerow([
                membership.user.get_full_name(),
                membership.user.username,
                membership.user.email,
                membership.membership_number or 'N/A',
                membership.get_plan_type_display(),
                membership.amount,
                membership.get_payment_method_display(),
                membership.get_status_display(),
                'Yes' if membership.is_active else 'No',
                membership.start_date.date() if membership.start_date else 'N/A',
                membership.end_date.date() if membership.end_date else 'N/A',
                membership.created_at.date()
            ])
        
        return response
    export_memberships.short_description = "Export selected memberships to CSV"

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
    list_display = ['name', 'vendor_display', 'price', 'stock', 'is_active', 'is_approved', 'created_at']
    list_filter = ['category', 'is_active', 'is_approved', 'created_at', 'vendor_user']
    search_fields = ['name', 'description', 'vendor', 'vendor_user__user__username', 'vendor_user__user__first_name', 'vendor_user__user__last_name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'is_approved', 'price', 'stock']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'description', 'price', 'stock', 'category', 'image', 'featured')
        }),
        ('Vendor Information', {
            'fields': ('vendor_user', 'vendor', 'approved_by', 'is_approved')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def vendor_display(self, obj):
        """Display vendor name in admin list"""
        return obj.get_vendor_name()
    vendor_display.short_description = 'Vendor'
    
    def save_model(self, request, obj, form, change):
        """Set approved_by when admin approves a product"""
        if change and 'is_approved' in form.changed_data and obj.is_approved:
            if hasattr(request.user, 'profile'):
                obj.approved_by = request.user.profile
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('vendor_user__user', 'approved_by__user')
    
    actions = ['approve_products', 'disapprove_products', 'activate_products', 'deactivate_products']
    
    def approve_products(self, request, queryset):
        """Bulk approve products"""
        approved_count = 0
        for product in queryset:
            if not product.is_approved:
                product.is_approved = True
                if hasattr(request.user, 'profile'):
                    product.approved_by = request.user.profile
                product.save()
                approved_count += 1
        self.message_user(request, f'{approved_count} products approved.')
    approve_products.short_description = "Approve selected products"
    
    def disapprove_products(self, request, queryset):
        """Bulk disapprove products"""
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} products disapproved.')
    disapprove_products.short_description = "Disapprove selected products"
    
    def activate_products(self, request, queryset):
        """Bulk activate products"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated.')
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        """Bulk deactivate products"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated.')
    deactivate_products.short_description = "Deactivate selected products"

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
