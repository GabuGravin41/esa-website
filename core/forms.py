from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    UserProfile, MembershipPlan, Membership,
    Event, EventRegistration, Product, Order,
    OrderItem, BlogPost, Comment, Resource,
    Payment, MpesaTransaction
)
import re

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('student_id', 'department', 'year_of_study', 'phone_number', 'bio', 'profile_picture')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = ('name', 'description', 'price', 'duration', 'features', 'is_active')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'features': forms.Textarea(attrs={'rows': 4}),
        }

class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ('user', 'plan', 'start_date', 'end_date', 'status', 'payment_status')
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = (
            'title', 'category', 'short_description', 'description', 
            'date', 'end_date', 'location', 'venue_type', 
            'capacity', 'price', 'speaker', 'registration_deadline', 
            'featured', 'image', 'status', 'is_active'
        )
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'registration_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = []  # No fields needed in the form, we'll set them in the view

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('name', 'description', 'price', 'stock', 'image', 'is_active')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('user', 'status', 'total_amount', 'payment_status')

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ('order', 'product', 'quantity', 'price')

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ('title', 'content', 'category', 'image', 'is_published')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

class CommentForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your comment here...'}), label='')
    
    class Meta:
        model = Comment
        fields = ['content']

class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ('title', 'description', 'category', 'file', 'link')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class MembershipPaymentForm(forms.Form):
    """Form for membership payment method selection"""
    PAYMENT_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-lg border border-gray-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-r-lg border border-gray-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '254XXXXXXXXX'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        phone_number = cleaned_data.get('phone_number')
        
        if payment_method == 'mpesa' and not phone_number:
            self.add_error('phone_number', 'Phone number is required for M-Pesa payments')
        
        return cleaned_data

class MpesaPaymentForm(forms.Form):
    """Form for M-Pesa payment"""
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'flex-1 rounded-r-lg border border-gray-300 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '254XXXXXXXXX'
        })
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        
        # Remove non-digit characters
        phone = re.sub(r'\D', '', phone)
        
        # Ensure it's a valid Kenyan number starting with 254
        if not phone.startswith('254') or len(phone) != 12:
            raise forms.ValidationError('Please enter a valid Kenyan phone number starting with 254')
            
        return phone 