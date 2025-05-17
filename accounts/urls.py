from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views
from .forms import LoginForm

urlpatterns = [
    # Redirect common login path to our custom login view
    #path('login/', RedirectView.as_view(pattern_name='account_login', permanent=False)),
    
    # Authentication views
    path('account_login/', views.login_view, name='account_login'),
    path('account_logout/', views.logout_view, name='account_logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    
    # API endpoints
    path('api/auth/status/', views.check_auth_status, name='auth_status'),
    
    # Password reset - Use Django's built-in views with custom templates
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
