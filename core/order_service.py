from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class OrderService:
    """Service for handling order operations"""
    
    @staticmethod
    def create_order(user, cart_items, total_amount, shipping_info=None):
        """
        Create a new order from cart items
        
        Args:
            user: The user placing the order
            cart_items: Items in the user's cart
            total_amount: Total order amount
            shipping_info: Dictionary containing shipping information
            
        Returns:
            The created order object
        """
        from core.models import Order, OrderItem, Payment, MpesaTransaction
        
        # Create the order
        order = Order.objects.create(
            user=user,
            total_amount=total_amount,
            status='pending',
            shipping_name=shipping_info.get('name', user.user.get_full_name() or user.user.username) if shipping_info else user.user.get_full_name() or user.user.username,
            shipping_address=shipping_info.get('address', '') if shipping_info else '',
            shipping_phone=shipping_info.get('phone', '') if shipping_info else '',
            shipping_email=shipping_info.get('email', user.user.email) if shipping_info else user.user.email,
        )
        
        # Create associated payment
        payment_method = shipping_info.get('payment_method', 'mpesa') if shipping_info else 'mpesa'
        payment = Payment.objects.create(
            user=user.user,
            amount=total_amount,
            currency='KES',
            payment_method=payment_method,
            status='pending',
        )
        
        # Create M-Pesa transaction if applicable
        if payment_method == 'mpesa':
            mpesa_tx = MpesaTransaction.objects.create(
                payment=payment,
                phone_number=shipping_info.get('phone', '') if shipping_info else '',
                amount=total_amount,  # Set the amount field to fix the NOT NULL constraint
                status='pending'
            )
        
        # Link payment to order
        order.payment = payment
        order.save()
        
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price,
                total_price=item['product'].price * item['quantity']
            )
            
            # Update product stock
            product = item['product']
            product.stock -= item['quantity']
            product.save()
        
        # Send order confirmation email
        try:
            from core.email_service import send_order_confirmation_email
            email_sent = send_order_confirmation_email(user, order)
            if not email_sent:
                logging.warning(f"Order confirmation email could not be sent for order {order.id}")
        except Exception as e:
            # Log error but don't stop order processing
            logging.error(f"Failed to send order confirmation email: {str(e)}")
            # Continue with order processing even if email fails
            
        return order
        
    @staticmethod
    def update_order_status(order, status, transaction_id=None):
        """
        Update order status and related payment information
        
        Args:
            order: The order to update
            status: The new status ('completed', 'processing', 'cancelled')
            transaction_id: Transaction ID from payment processor
        
        Returns:
            The updated order
        """
        # Update order status
        order.status = status
        
        # If completed, update payment status
        if status == 'completed':
            order.payment_status = True
            
            # Update payment if it exists
            if hasattr(order, 'payment'):
                order.payment.status = 'completed'
                if transaction_id:
                    order.payment.transaction_id = transaction_id
                order.payment.save()
        
        order.save()
        
        # Send email based on status
        try:
            if status == 'completed':
                from core.email_service import send_order_confirmation_email
                send_order_confirmation_email(order.user, order)
            elif status == 'cancelled':
                # Could implement a cancellation email here
                pass
        except Exception as e:
            logger.error(f"Failed to send order status update email: {str(e)}")
            
        return order
