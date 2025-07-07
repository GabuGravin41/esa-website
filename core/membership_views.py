import json
import logging
import random
import string
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    Payment, MpesaTransaction, Membership, UserProfile
)
from .services import MpesaService

# Helper function to generate a membership number
def generate_membership_number():
    """Generate a unique membership number"""
    year = datetime.now().year
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    membership_number = f"ESA-{year}-{random_chars}"
    
    # Check if membership number already exists
    while Membership.objects.filter(membership_number=membership_number).exists():
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        membership_number = f"ESA-{year}-{random_chars}"
    
    return membership_number

@login_required
@require_POST
def process_mpesa_membership(request):
    """Process M-Pesa payment for membership"""
    try:
        # Get form data
        plan_type = request.POST.get('plan_type')
        amount = request.POST.get('amount')
        phone_number = request.POST.get('phone_number')
        
        # Validate the data
        if not all([plan_type, amount, phone_number]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=amount,
            currency='KES',
            payment_method='mpesa',
            status='pending',
            notes=f'Membership payment for {plan_type} plan'
        )
        
        # Create membership record (initially inactive)
        start_date = timezone.now()
        end_date = start_date + timedelta(days=365)  # 1 year membership
        
        membership = Membership.objects.create(
            user=request.user,
            plan_type=plan_type,
            amount=amount,
            payment_method='mpesa',
            status='pending',
            is_active=False,
            start_date=start_date,
            end_date=end_date,
            membership_number=generate_membership_number(),
            payment=payment
        )
        
        # Link payment to membership (both ways)
        payment.membership = membership
        payment.save()
        
        # Create M-Pesa transaction record
        mpesa_tx = MpesaTransaction.objects.create(
            payment=payment,
            phone_number=phone_number,
            amount=amount,
            status='pending'
        )
        
        # Initiate STK push
        mpesa_service = MpesaService()
        reference = f"ESA-MEM-{payment.id}"
        description = f"ESA Membership: {plan_type}"
        
        try:
            response = mpesa_service.initiate_stk_push(
                phone_number=phone_number,
                amount=float(amount),
                reference=reference,
                description=description
            )
            
            if 'CheckoutRequestID' in response:
                mpesa_tx.checkout_request_id = response['CheckoutRequestID']
                mpesa_tx.merchant_request_id = response.get('MerchantRequestID')
                mpesa_tx.save(update_fields=['checkout_request_id', 'merchant_request_id'])
                
                return JsonResponse({
                    'success': True, 
                    'checkout_request_id': response['CheckoutRequestID'],
                    'payment_id': payment.id
                })
            else:
                return JsonResponse({'success': False, 'error': 'Failed to initiate payment'})
                
        except Exception as e:
            logging.error(f"STK push error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
            
    except Exception as e:
        logging.error(f"Process M-Pesa membership error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def check_membership_payment_status(request):
    """Check the status of a membership payment"""
    try:
        # Get the request data
        data = json.loads(request.body)
        checkout_request_id = data.get('checkout_request_id')
        payment_id = data.get('payment_id')
        
        if not checkout_request_id or not payment_id:
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
            
        # Get the payment and transaction
        try:
            payment = Payment.objects.get(id=payment_id, user=request.user)
            mpesa_tx = payment.mpesa_transaction
        except (Payment.DoesNotExist, AttributeError):
            return JsonResponse({'success': False, 'error': 'Payment not found'})
        
        # If already completed, return success
        if payment.status == 'completed' and hasattr(payment, 'membership'):
            membership = payment.membership
            return JsonResponse({
                'success': True,
                'status': 'completed',
                'message': 'Payment was successful',
                'member_number': membership.membership_number,
                'redirect_url': f'/membership/payment-success/?membership_id={membership.id}'
            })
        
        # Check transaction status with M-Pesa
        mpesa_service = MpesaService()
        try:
            status_response = mpesa_service.query_transaction_status(checkout_request_id)
            
            result_code = status_response.get('ResultCode')
            
            if result_code == '0':  # Success
                # Update transaction and payment
                mpesa_tx.status = 'completed'
                mpesa_tx.result_code = result_code
                mpesa_tx.result_description = status_response.get('ResultDesc')
                mpesa_tx.save()
                
                # Complete payment
                payment.status = 'completed'
                payment.save()
                
                # Activate membership
                membership = payment.membership
                membership.status = 'completed'
                membership.is_active = True
                membership.save()
                
                # Update user profile
                profile = UserProfile.objects.get(user=request.user)
                profile.membership_status = 'active'
                profile.membership_expiry = membership.end_date
                profile.save()
                
                return JsonResponse({
                    'success': True,
                    'status': 'completed',
                    'message': 'Payment was successful',
                    'member_number': membership.membership_number,
                    'redirect_url': f'/membership/payment-success/?membership_id={membership.id}'
                })
            
            elif result_code == '1037':  # Timeout
                return JsonResponse({
                    'success': True,
                    'status': 'pending',
                    'message': 'Payment is still being processed'
                })
                
            else:  # Failed
                mpesa_tx.status = 'failed'
                mpesa_tx.result_code = result_code
                mpesa_tx.result_description = status_response.get('ResultDesc')
                mpesa_tx.save()
                
                payment.status = 'failed'
                payment.save()
                
                return JsonResponse({
                    'success': False,
                    'status': 'failed',
                    'message': status_response.get('ResultDesc', 'Payment failed')
                })
                
        except Exception as e:
            logging.error(f"Error checking payment status: {str(e)}")
            return JsonResponse({
                'success': True,
                'status': 'pending',
                'message': 'Unable to verify payment status. Please try again later.'
            })
    
    except Exception as e:
        logging.error(f"Check payment status error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def verify_mpesa_membership(request):
    """Verify manually entered M-Pesa transaction code"""
    try:
        # Get the request data
        data = json.loads(request.body)
        mpesa_code = data.get('mpesa_code')
        plan_type = data.get('plan_type')
        amount = data.get('amount')
        
        if not mpesa_code or not plan_type or not amount:
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
            
        # Check if this code has already been used
        if MpesaTransaction.objects.filter(mpesa_receipt=mpesa_code).exists():
            return JsonResponse({'success': False, 'error': 'This M-Pesa transaction code has already been used'})
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=amount,
            currency='KES',
            payment_method='mpesa',
            status='completed',  # Assume the payment is valid
            transaction_id=mpesa_code,
            notes=f'Membership payment for {plan_type} plan (manual verification)'
        )
        
        # Create membership record
        start_date = timezone.now()
        end_date = start_date + timedelta(days=365)  # 1 year membership
        
        membership = Membership.objects.create(
            user=request.user,
            plan_type=plan_type,
            amount=amount,
            payment_method='mpesa',
            status='completed',
            is_active=True,
            start_date=start_date,
            end_date=end_date,
            membership_number=generate_membership_number(),
            payment=payment
        )
        
        # Link payment to membership (both ways)
        payment.membership = membership
        payment.save()
        
        # Create M-Pesa transaction record
        mpesa_tx = MpesaTransaction.objects.create(
            payment=payment,
            phone_number=request.user.userprofile.phone if hasattr(request.user, 'userprofile') else '',
            amount=amount,
            status='completed',
            mpesa_receipt=mpesa_code,
            transaction_date=timezone.now()
        )
        
        # Update user profile
        profile = UserProfile.objects.get(user=request.user)
        profile.membership_status = 'active'
        profile.membership_expiry = membership.end_date
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Payment verified successfully',
            'redirect_url': f'/membership/payment-success/?membership_id={membership.id}'
        })
        
    except Exception as e:
        logging.error(f"Verify M-Pesa membership error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def membership_payment_success(request):
    """Show the membership payment success page"""
    membership_id = request.GET.get('membership_id')
    
    if not membership_id:
        messages.error(request, 'No membership information provided')
        return redirect('membership')
    
    try:
        membership = Membership.objects.get(id=membership_id, user=request.user)
    except Membership.DoesNotExist:
        messages.error(request, 'Membership not found')
        return redirect('membership')
    
    return render(request, 'core/membership_success.html', {'membership': membership})

@login_required
def process_paypal_membership(request):
    """Process PayPal payment for membership (placeholder)"""
    return JsonResponse({
        'success': False, 
        'error': 'PayPal payment is not fully implemented yet. Please use M-Pesa.'
    })
