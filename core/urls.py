from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    # URLs
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # New URL patterns for header links
    path('constitution/', views.constitution, name='constitution'),
    path('journals/', views.esa_journals, name='esa_journals'),
    path('more-sites/', views.more_sites, name='more_sites'),
    path('more-sites/add/', views.suggest_resource, name='add_resource_link'),
    path('more-sites/suggest/', views.site_form, name='site_form'),
    path('more-sites/manage/', views.manage_sites, name='manage_sites'),
    path('more-sites/approve/<int:site_id>/', views.approve_site, name='approve_site'),
    path('more-sites/reject/<int:site_id>/', views.reject_site, name='reject_site'),
    path('more-sites/edit/<int:site_id>/', views.edit_site, name='edit_site'),
    path('more-sites/delete/<int:site_id>/', views.delete_site, name='delete_site'),
    path('more-sites/admin-add/', views.admin_add_site, name='admin_add_site'),
    path('donate/', views.donate, name='donate'),
    
    # Protected URLs (require login)
    path('membership/', views.membership, name='membership'),
    path('membership/join/<int:plan_id>/', views.join_membership, name='join_membership'),
    path('membership/payment/<int:payment_id>/mpesa/', views.mpesa_payment, name='mpesa_payment'),
    path('membership/payment/<int:payment_id>/paypal/', views.paypal_payment, name='paypal_payment'),
    path('membership/payment/<int:payment_id>/status/', views.payment_status, name='payment_status'),
    path('membership/payment/<int:payment_id>/receipt/', views.generate_receipt, name='generate_receipt'),
    path('membership/payment/history/', views.payment_history, name='payment_history'),
    path('membership/payment/paypal/success/<int:payment_id>/', views.paypal_success, name='paypal_success'),
    path('membership/payment/paypal/cancel/<int:payment_id>/', views.paypal_cancel, name='paypal_cancel'),
    path('membership/payment/mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('process-membership/', views.process_membership, name='process_membership'),
    
    # Member-Get-a-Member URLs
    path('membership/refer/', views.member_get_member, name='member_get_member'),
    path('membership/refer/payment/<int:payment_id>/mpesa/', views.mgm_mpesa_payment, name='mgm_mpesa_payment'),
    path('membership/refer/payment/<int:payment_id>/paypal/', views.mgm_paypal_payment, name='mgm_paypal_payment'),
    path('membership/refer/payment/paypal/success/<int:payment_id>/', views.mgm_paypal_success, name='mgm_paypal_success'),
    path('membership/refer/payment/paypal/cancel/<int:payment_id>/', views.mgm_paypal_cancel, name='mgm_paypal_cancel'),
    
    # Events URLs
    path('events/', views.events, name='events'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:event_id>/register/', views.event_register, name='event_register'),
    path('events/<int:event_id>/cancel/', views.event_cancel_registration, name='event_cancel_registration'),
    path('events/suggest/', views.event_suggestion, name='event_suggestion'),
    
    # Store URLs
    path('store/', views.store, name='store'),
    path('store/create/', views.product_create, name='product_create'),
    path('store/<slug:slug>/', views.product_detail, name='product_detail'),
    path('store/<slug:slug>/edit/', views.product_edit, name='product_edit'),
    path('store/<slug:slug>/delete/', views.product_delete, name='product_delete'),
    path('cart/', views.cart, name='cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
    
    # Blog URLs
    path('blog/', views.blog, name='blog'),
    path('blog/post/<int:post_id>/', views.blog_post_detail, name='blog_post_detail'),
    path('blog/create/', views.blog_post_create, name='blog_post_create'),
    path('blog/post/<int:post_id>/edit/', views.blog_post_edit, name='blog_post_edit'),
    path('blog/post/<int:post_id>/delete/', views.blog_post_delete, name='blog_post_delete'),
    # Add this alias
    path('blog/<int:post_id>/', views.blog_post_detail, name='blog_detail'),
    
    # Resources URLs
    path('resources/', views.resources, name='resources'),
    path('resources/create/', views.resource_create, name='resource_create'),
    path('resources/<int:resource_id>/', views.resource_detail, name='resource_detail'),
    path('resources/<int:resource_id>/edit/', views.resource_edit, name='resource_edit'),
    path('resources/<int:resource_id>/delete/', views.resource_delete, name='resource_delete'),
    path('resources/<int:resource_id>/download/', views.resource_download, name='resource_download'),
    path('resources/suggest/', views.suggest_resource, name='suggest_resource'),
    path('resources/add-link/', views.add_resource_link, name='add_resource_link'),

    # Communities URLs
    path('communities/', views.communities, name='communities'),
    path('community/create/', views.create_community, name='create_community'),
    path('community/<slug:slug>/', views.community_detail, name='community_detail'),
    path('community/<slug:slug>/edit/', views.edit_community, name='edit_community'),
    path('community/<slug:slug>/join/', views.join_community, name='join_community'),
    path('community/<slug:slug>/leave/', views.leave_community, name='leave_community'),
    path('community/<slug:slug>/members/', views.community_members, name='community_members'),
    path('community/<slug:community_slug>/members/promote/<int:user_id>/', views.promote_member, name='promote_member'),
    path('community/<slug:community_slug>/members/remove/<int:user_id>/', views.remove_member, name='remove_member'),
    path('community/<slug:slug>/discussions/', views.community_discussions, name='community_discussions'),
    path('community/<slug:slug>/events/', views.community_events, name='community_events'),
    path('community/<slug:community_slug>/discussion/create/', views.create_discussion, name='create_discussion'),
    path('community/<slug:community_slug>/discussion/<slug:slug>/', views.discussion_detail, name='discussion_detail'),
    path('community/<slug:community_slug>/event/create/', views.create_event, name='create_event'),
    path('community/<slug:community_slug>/event/<slug:slug>/', views.community_event_detail, name='event_detail'),
    path('community/<slug:community_slug>/event/<slug:slug>/attend/', views.attend_event, name='attend_event'),
    path('community/<slug:community_slug>/event/<slug:slug>/leave/', views.leave_event, name='leave_event'),

    # Dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Admin URLs
    path('admin/permissions/', views.permission_management, name='permission_management'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),  # New admin dashboard
    path('admin/init-admin-users/', views.init_admin_users, name='init_admin_users'),  # Initialize admin users

    # Search URLs
    path('search/', views.search, name='search'),
    
]

# Add media URL configuration in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)