from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    # Public URLs
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    
    # Protected URLs (require login)
    path('membership/', views.membership, name='membership'),
    path('membership/join/<int:plan_id>/', views.join_membership, name='join_membership'),
    path('membership/payment/<int:payment_id>/mpesa/', views.mpesa_payment, name='mpesa_payment'),
    path('membership/payment/<int:payment_id>/paypal/', views.paypal_payment, name='paypal_payment'),
    path('membership/payment/<int:payment_id>/status/', views.payment_status, name='payment_status'),
    path('membership/payment/paypal/success/<int:payment_id>/', views.paypal_success, name='paypal_success'),
    path('membership/payment/paypal/cancel/<int:payment_id>/', views.paypal_cancel, name='paypal_cancel'),
    path('membership/payment/mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Events URLs
    path('events/', views.events, name='events'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:event_id>/register/', views.event_register, name='event_register'),
    path('events/<int:event_id>/cancel/', views.event_cancel_registration, name='event_cancel_registration'),
    
    path('store/', views.store, name='store'),
    path('store/product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    path('blog/', views.blog, name='blog'),
    path('blog/post/<int:post_id>/', views.blog_post_detail, name='blog_post_detail'),
    path('blog/create/', views.blog_post_create, name='blog_post_create'),
    path('blog/post/<int:post_id>/edit/', views.blog_post_edit, name='blog_post_edit'),
    path('blog/post/<int:post_id>/delete/', views.blog_post_delete, name='blog_post_delete'),
    
    path('resources/', views.resources, name='resources'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
