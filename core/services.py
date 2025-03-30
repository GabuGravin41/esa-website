import base64
import json
import requests
from datetime import datetime
from django.conf import settings
from django.utils import timezone

class MpesaService:
    """Service class for handling M-Pesa transactions"""
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        self.access_token = self._get_access_token()
        
    def _get_access_token(self):
        """Get OAuth access token from Safaricom"""
        url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        
        # Create auth string and encode it to base64
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        auth_bytes = auth_string.encode("ascii")
        base64_bytes = base64.b64encode(auth_bytes)
        base64_auth = base64_bytes.decode("ascii")
        
        headers = {
            "Authorization": f"Basic {base64_auth}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response_data = response.json()
            return response_data.get('access_token')
        except Exception as e:
            print(f"Error getting M-Pesa access token: {e}")
            return None
    
    def _generate_password(self):
        """Generate M-Pesa password for STK push"""
        data_to_encode = f"{self.shortcode}{self.passkey}{self.timestamp}"
        encoded = base64.b64encode(data_to_encode.encode())
        return encoded.decode('utf-8')
    
    def initiate_stk_push(self, phone_number, amount, reference, description):
        """Initiate M-Pesa STK push request"""
        if not self.access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        # Ensure phone number starts with 254 and no + sign
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._generate_password(),
            "Timestamp": self.timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": reference,
            "TransactionDesc": description
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Error initiating STK push: {e}")
            return {
                "status": "error",
                "message": f"Failed to initiate payment: {str(e)}"
            }
    
    def query_transaction_status(self, checkout_request_id):
        """Query the status of an M-Pesa transaction"""
        if not self.access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._generate_password(),
            "Timestamp": self.timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Error querying transaction status: {e}")
            return {
                "status": "error",
                "message": f"Failed to query transaction: {str(e)}"
            }

class PayPalService:
    """Service class for handling PayPal transactions"""
    
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.mode = settings.PAYPAL_MODE  # 'sandbox' or 'live'
        self.access_token = self._get_access_token()
        
    def _get_access_token(self):
        """Get OAuth access token from PayPal"""
        base_url = "https://api.sandbox.paypal.com" if self.mode == 'sandbox' else "https://api.paypal.com"
        url = f"{base_url}/v1/oauth2/token"
        
        # Create auth string and encode it to base64
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode("ascii")
        base64_bytes = base64.b64encode(auth_bytes)
        base64_auth = base64_bytes.decode("ascii")
        
        headers = {
            "Authorization": f"Basic {base64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = "grant_type=client_credentials"
        
        try:
            response = requests.post(url, headers=headers, data=payload)
            response_data = response.json()
            return response_data.get('access_token')
        except Exception as e:
            print(f"Error getting PayPal access token: {e}")
            return None
    
    def create_order(self, amount, currency, reference, return_url, cancel_url):
        """Create a PayPal order for payment"""
        if not self.access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        base_url = "https://api.sandbox.paypal.com" if self.mode == 'sandbox' else "https://api.paypal.com"
        url = f"{base_url}/v2/checkout/orders"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference,
                    "amount": {
                        "currency_code": currency,
                        "value": str(amount)
                    },
                    "description": f"ESA-KU Membership Payment: {reference}"
                }
            ],
            "application_context": {
                "brand_name": "ESA-KU",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": return_url,
                "cancel_url": cancel_url
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Error creating PayPal order: {e}")
            return {
                "status": "error",
                "message": f"Failed to create PayPal order: {str(e)}"
            }
    
    def capture_order(self, order_id):
        """Capture payment for a previously created order"""
        if not self.access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        base_url = "https://api.sandbox.paypal.com" if self.mode == 'sandbox' else "https://api.paypal.com"
        url = f"{base_url}/v2/checkout/orders/{order_id}/capture"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Error capturing PayPal order: {e}")
            return {
                "status": "error",
                "message": f"Failed to capture PayPal order: {str(e)}"
            } 