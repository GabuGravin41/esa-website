from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from core.models import UserProfile

class LoginForm(AuthenticationForm):
    """Custom login form with additional styling"""
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                'placeholder': 'Username',
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                'placeholder': 'Password',
            }
        )
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            }
        )
    )

class UserRegistrationForm(UserCreationForm):
    """User registration form with email field and validation"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                'placeholder': 'Email address',
            }
        )
    )
    
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                'placeholder': 'Username',
            }
        )
    )
    
    student_id = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                'placeholder': 'Student Registration Number',
            }
        )
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                'placeholder': 'Password',
            }
        )
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                'placeholder': 'Confirm Password',
            }
        )
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'student_id', 'password1', 'password2')
    
    def clean_email(self):
        """Ensure email is unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email
    
    def clean_username(self):
        """Additional username validation"""
        username = self.cleaned_data.get('username')
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters long.')
        return username
        
    def clean_student_id(self):
        """Ensure student ID is unique"""
        student_id = self.cleaned_data.get('student_id')
        if UserProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('This student ID is already registered.')
        return student_id

    def save(self, commit=True):
        """Save the user with the email field"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Update the profile with the student_id
            try:
                user.profile.student_id = self.cleaned_data['student_id']
                user.profile.save()
            except Exception as e:
                # This should not happen as the profile is created by signal
                pass
        return user

class UserProfileForm(forms.ModelForm):
    """Form for editing UserProfile"""
    student_id = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'w-full p-2 border rounded focus:outline-none focus:border-blue-500'}
        )
    )
    department = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'w-full p-2 border rounded focus:outline-none focus:border-blue-500'}
        )
    )
    year_of_study = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={'class': 'w-full p-2 border rounded focus:outline-none focus:border-blue-500'}
        )
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'w-full p-2 border rounded focus:outline-none focus:border-blue-500'}
        )
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'rows': 4, 'class': 'w-full p-2 border rounded focus:outline-none focus:border-blue-500'}
        )
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={'class': 'w-full p-2 border rounded focus:outline-none focus:border-blue-500'}
        )
    )
    
    class Meta:
        model = UserProfile
        fields = ('student_id', 'department', 'year_of_study', 'phone_number', 'bio', 'profile_picture')
    
    def clean_student_id(self):
        """Ensure student ID is unique"""
        student_id = self.cleaned_data.get('student_id')
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # Exclude the current instance when checking for duplicates
            if UserProfile.objects.filter(student_id=student_id).exclude(pk=instance.pk).exists():
                raise forms.ValidationError('This student ID is already registered.')
        else:
            # For new instances, just check if it exists
            if UserProfile.objects.filter(student_id=student_id).exists():
                raise forms.ValidationError('This student ID is already registered.')
        return student_id 