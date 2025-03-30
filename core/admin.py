from django.contrib import admin
from .models import (
    UserProfile, MembershipPlan, Membership,
    Event, EventRegistration, Product, Order,
    OrderItem, BlogPost, Comment, Resource
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'department', 'year_of_study', 'phone_number')
    search_fields = ('user__username', 'student_id', 'department')
    list_filter = ('department', 'year_of_study')

@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('is_active',)

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'status', 'payment_status')
    search_fields = ('user__user__username', 'plan__name')
    list_filter = ('status', 'payment_status', 'plan')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'capacity', 'price', 'is_active')
    search_fields = ('title', 'description', 'location')
    list_filter = ('is_active', 'date')

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'registration_date', 'status', 'payment_status')
    search_fields = ('event__title', 'user__user__username')
    list_filter = ('status', 'payment_status')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('is_active',)

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
    list_display = ('post', 'author', 'created_at')
    search_fields = ('content', 'author__user__username', 'post__title')
    list_filter = ('created_at',)

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'uploaded_by', 'created_at')
    search_fields = ('title', 'description', 'uploaded_by__user__username')
    list_filter = ('category', 'created_at')
