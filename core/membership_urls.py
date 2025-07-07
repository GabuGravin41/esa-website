from django.urls import path

from . import membership_views

membership_urlpatterns = [
    # Membership payment URLs
    path('membership/process-mpesa/', membership_views.process_mpesa_membership, name='process_mpesa_membership'),
    path('membership/process-paypal/', membership_views.process_paypal_membership, name='process_paypal_membership'),
    path('membership/check-payment-status/', membership_views.check_membership_payment_status, name='check_membership_payment_status'),
    path('membership/verify-mpesa-payment/', membership_views.verify_mpesa_membership, name='verify_mpesa_membership'),
    path('membership/payment-success/', membership_views.membership_payment_success, name='membership_payment_success'),
]
