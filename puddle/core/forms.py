from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    UserProfile, MembershipPlan, Membership,
    Event, EventRegistration, Product, Order,
    OrderItem, BlogPost, Comment, Resource,
    Payment, MpesaTransaction, Contact, Community, Discussion
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

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'subject', 'message']

class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = ['name', 'plan_type', 'price', 'duration', 'is_active']

class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ['plan_type', 'payment_method']

class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'slug', 'description', 'category', 'image', 'rules', 'is_private']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'slug': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'image': forms.FileInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'rules': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 5}),
            'is_private': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'}),
        }

class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'content': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 10}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 3, 'placeholder': 'Add your comment...'}),
        }
        labels = {
            'content': '',
        }

class EventForm(forms.ModelForm):
    start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    
    end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_type', 'location', 'online_link', 'start_date', 'end_date', 'image', 'is_active', 'featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 5}),
            'event_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'location': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'online_link': forms.URLInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'image': forms.FileInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'}),
            'featured': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        event_type = cleaned_data.get('event_type')
        location = cleaned_data.get('location')
        online_link = cleaned_data.get('online_link')
        
        # Validate dates
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date cannot be before start date")
        
        # Validate event type specifics
        if event_type == 'in_person' and not location:
            self.add_error('location', "Location is required for in-person events")
        
        if event_type == 'virtual' and not online_link:
            self.add_error('online_link', "Online link is required for virtual events")
        
        if event_type == 'hybrid' and (not location or not online_link):
            if not location:
                self.add_error('location', "Location is required for hybrid events")
            if not online_link:
                self.add_error('online_link', "Online link is required for hybrid events")
        
        return cleaned_data

class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = []  # No fields needed in the form, we'll set them in the view

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'slug', 'description', 'price', 'stock', 'category', 'vendor', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'slug': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'stock': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'category': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'vendor': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'image': forms.FileInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
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

class ResourceForm(forms.ModelForm):
    """Form for creating and editing resources"""
    tags = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-role': 'tagsinput'})
    )
    
    class Meta:
        model = Resource
        fields = ['title', 'description', 'category', 'file', 'thumbnail', 'link', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-4 border border-gray-200 rounded-xl'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-4 border border-gray-200 rounded-xl'}),
            'category': forms.Select(attrs={'class': 'w-full p-4 border border-gray-200 rounded-xl'}),
            'file': forms.FileInput(attrs={'class': 'w-full p-4 border border-gray-200 rounded-xl'}),
            'thumbnail': forms.FileInput(attrs={'class': 'w-full p-4 border border-gray-200 rounded-xl'}),
            'link': forms.URLInput(attrs={'class': 'w-full p-4 border border-gray-200 rounded-xl'}),
        }
        
    def __init__(self, *args, **kwargs):
        super(ResourceForm, self).__init__(*args, **kwargs)
        
        # Make only certain fields required based on category
        self.fields['file'].required = False
        self.fields['thumbnail'].required = False
        self.fields['link'].required = False
        
        # If instance exists, pre-populate tags field
        if self.instance.pk:
            self.fields['tags'].initial = ", ".join([tag.name for tag in self.instance.tags.all()])
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        file = cleaned_data.get('file')
        link = cleaned_data.get('link')
        
        if category in ['pdf', 'document', 'code', 'video', 'image', 'audio']:
            if not file and not self.instance.file:
                self.add_error('file', 'File is required for this category')
        elif category == 'link':
            if not link:
                self.add_error('link', 'URL is required for link resources')
        
        return cleaned_data
    
    def save(self, commit=True):
        resource = super(ResourceForm, self).save(commit=False)
        
        if commit:
            resource.save()
            
            # Handle tags
            if 'tags' in self.cleaned_data:
                # First remove all existing tags
                resource.tags.clear()
                
                # Add new tags
                tags_string = self.cleaned_data['tags']
                tag_list = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
                
                for tag_name in tag_list:
                    tag, created = ResourceTag.objects.get_or_create(name=tag_name)
                    resource.tags.add(tag)
        
        return resource

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

class MemberGetMemberForm(forms.Form):
    referred_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                        'placeholder': 'Enter email address'}),
        help_text="Enter the email address of the person you'd like to pay for."
    )
    
    student_id = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                      'placeholder': 'Enter student registration number'}),
        help_text="Enter the student registration number of the person you'd like to pay for."
    )
    
    plan_type = forms.ChoiceField(
        choices=MembershipPlan.PLAN_TYPES,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )
    
    payment_method = forms.ChoiceField(
        choices=[('mpesa', 'M-Pesa'), ('paypal', 'PayPal')],
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )
    
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                      'placeholder': '254XXXXXXXXX'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        phone_number = cleaned_data.get('phone_number')
        referred_email = cleaned_data.get('referred_email')
        student_id = cleaned_data.get('student_id')
        
        # Validate phone number for M-Pesa
        if payment_method == 'mpesa' and not phone_number:
            self.add_error('phone_number', 'Phone number is required for M-Pesa payments')
        
        # Validate that the referred email exists
        if referred_email:
            try:
                user = User.objects.get(email=referred_email)
            except User.DoesNotExist:
                self.add_error('referred_email', 'This email is not registered. The user must create an account first.')
        
        # Validate that the student ID is valid (not already in use by someone else)
        if student_id and referred_email:
            try:
                # Check if email exists
                user = User.objects.get(email=referred_email)
                
                # Check if student ID is already in use by a different user
                existing_profile = UserProfile.objects.filter(student_id=student_id).exclude(user=user).first()
                if existing_profile:
                    self.add_error('student_id', 'This student ID is already associated with a different user.')
            except User.DoesNotExist:
                # This was already handled in the email validation above
                pass
        
        return cleaned_data

class EventSuggestionForm(forms.Form):
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003366]', 'id': 'eventTitle'})
    )
    type = forms.ChoiceField(
        choices=Event.EVENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003366]', 'id': 'eventType'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003366]', 'rows': 3, 'id': 'eventDescription'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003366]'})
    )
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long")
        return title
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if len(description) < 20:
            raise forms.ValidationError("Please provide a more detailed description (at least 20 characters)")
        return description