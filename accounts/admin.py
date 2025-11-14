from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from core.models import UserProfile
from django.utils import timezone
from django.contrib import messages

# Define an inline admin descriptor for UserProfile model
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    
    # Fields to show in the inline form
    fields = ('student_id', 'department', 'course', 'year_of_study', 
              'phone_number', 'membership_number', 'membership_status', 
              'membership_expiry', 'user_type')

# Define a new User admin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_membership_number', 'get_membership_status')
    list_select_related = ('profile', )
    actions = ['generate_member_numbers', 'activate_memberships']
    
    def get_membership_number(self, obj):
        try:
            return obj.profile.membership_number
        except UserProfile.DoesNotExist:
            return "No profile"
    get_membership_number.short_description = 'Member Number'
    get_membership_number.admin_order_field = 'profile__membership_number'
    
    def get_membership_status(self, obj):
        try:
            return obj.profile.get_membership_status_display()
        except UserProfile.DoesNotExist:
            return "No profile"
    get_membership_status.short_description = 'Membership Status'
    get_membership_status.admin_order_field = 'profile__membership_status'
    
    def generate_member_numbers(self, request, queryset):
        """Generate membership numbers for selected users"""
        count = 0
        for user in queryset:
            try:
                profile = UserProfile.objects.get(user=user)
                if not profile.membership_number:
                    profile.generate_membership_number()
                    count += 1
            except UserProfile.DoesNotExist:
                # Create a profile with default values
                profile = UserProfile(
                    user=user,
                    student_id=f"USER{user.id:05d}",  # Default student ID format
                    department="Not specified",
                    year_of_study=1,
                )
                profile.save()
                profile.generate_membership_number()
                count += 1
        
        self.message_user(request, f"Generated membership numbers for {count} users.")
    generate_member_numbers.short_description = "Generate membership numbers"
    
    def activate_memberships(self, request, queryset):
        """Activate memberships for selected users"""
        count = 0
        for user in queryset:
            try:
                profile = UserProfile.objects.get(user=user)
                if profile.membership_status != 'active':
                    profile.membership_status = 'active'
                    # Set expiry to 1 year from now if not set
                    if not profile.membership_expiry:
                        profile.membership_expiry = timezone.now().date().replace(
                            year=timezone.now().year + 1
                        )
                    # Ensure they have a membership number
                    if not profile.membership_number:
                        profile.generate_membership_number()
                    profile.save()
                    count += 1
            except UserProfile.DoesNotExist:
                # Create a profile with active membership
                profile = UserProfile(
                    user=user,
                    student_id=f"USER{user.id:05d}",  # Default student ID format
                    department="Not specified",
                    year_of_study=1,
                    membership_status='active',
                    membership_expiry=timezone.now().date().replace(
                        year=timezone.now().year + 1
                    )
                )
                profile.save()
                profile.generate_membership_number()
                count += 1
        
        self.message_user(request, f"Activated memberships for {count} users.")
    activate_memberships.short_description = "Activate memberships"
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)
    
    def save_model(self, request, obj, form, change):
        """Create a profile when a user is created if it doesn't exist"""
        super().save_model(request, obj, form, change)
        
        if not change:  # Only for new users
            try:
                # Check if profile exists
                UserProfile.objects.get(user=obj)
            except UserProfile.DoesNotExist:
                # Create a default profile
                profile = UserProfile(
                    user=obj,
                    student_id=f"USER{obj.id:05d}",  # Default student ID format
                    department="Not specified",
                    year_of_study=1,
                    membership_status='inactive'  # Default to inactive until payment
                )
                profile.save()
                messages.info(request, f"Created profile for user {obj.username}. Membership is inactive until payment is confirmed.")

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)