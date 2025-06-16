import base64
import json
import requests
import base64
import logging
import random
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class MpesaService:
    def __init__(self):
        self.business_shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.environment = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        
        # Special handling for callback URL in development/sandbox
        callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        site_url = getattr(settings, 'SITE_URL', '')
        
        # When in development but not using localhost
        if settings.DEBUG and site_url and not ('localhost' in callback_url or '127.0.0.1' in callback_url):
            # Construct callback URL using SITE_URL if available
            if not callback_url.startswith('http'):
                if site_url.endswith('/'):
                    site_url = site_url[:-1]  # Remove trailing slash
                
                # Use /payment/mpesa/callback/ as the default path
                if not callback_url:
                    callback_url = f"{site_url}/payment/mpesa/callback/"
                elif callback_url.startswith('/'):
                    callback_url = f"{site_url}{callback_url}"
                else:
                    callback_url = f"{site_url}/{callback_url}"
                    
                logging.info(f"Constructed M-Pesa callback URL: {callback_url}")
        
        # When in sandbox mode, if URL is localhost or 127.0.0.1, use a dummy URL
        if self.environment == 'sandbox' and ('localhost' in callback_url or '127.0.0.1' in callback_url):
            self.callback_url = 'https://sandbox.safaricom.co.ke/mpesa/'  # Special URL for sandbox testing
            logging.warning("Using sandbox dummy callback URL as local URLs won't work with M-Pesa API")
        else:
            self.callback_url = callback_url
            
        # Use getattr with default to handle missing MPESA_REFERENCE
        self.reference = getattr(settings, 'MPESA_REFERENCE', 'ESA-KU')
        self.base_url = 'https://sandbox.safaricom.co.ke' if self.environment == 'sandbox' else 'https://api.safaricom.co.ke'

    def get_access_token(self):
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        headers = {'Authorization': f'Basic {auth}'}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            raise Exception(f"Failed to get access token: {str(e)}")

    def initiate_stk_push(self, phone_number, amount, reference, description):
        """Initiate STK push for payment"""
        try:
            # Special handling for development mode with simulated success
            if settings.DEBUG and getattr(settings, 'MPESA_SIMULATE_IN_DEV', True):
                # Create a unique request ID for development testing
                dev_request_id = f"ws_{int(timezone.now().timestamp())}_{random.randint(1000, 9999)}"
                logging.info(f"DEVELOPMENT MODE: Simulated STK Push with request ID {dev_request_id}")
                
                # Return simulated success response
                return {
                    'MerchantRequestID': f'dev-{dev_request_id}',
                    'CheckoutRequestID': dev_request_id,
                    'ResponseCode': '0',
                    'ResponseDescription': 'Success. Request accepted for processing',
                    'CustomerMessage': 'Development mode: Success. Request accepted for processing'
                }
            
            # Debug information
            logging.info(f"Initiating STK push with: Phone={phone_number}, Amount={amount}, Reference={reference}")
            logging.info(f"Using M-Pesa settings: ShortCode={self.business_shortcode}, Environment={self.environment}, CallbackURL={self.callback_url}")
            
            # Ensure phone number is in the correct format (254XXXXXXXXX)
            # Remove any leading + or spaces
            phone_number = phone_number.strip().replace('+', '')
            
            # If the phone number starts with 0, replace it with 254
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            # If it doesn't start with 254, add it
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number
                
            # Validate the phone number format
            if not phone_number.isdigit() or len(phone_number) != 12:
                raise ValueError(f"Invalid phone number format: {phone_number}. Must be 12 digits in format 254XXXXXXXXX")
            
            # Get access token
            access_token = self.get_access_token()
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare payload
            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": self.business_shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": self.callback_url,
                "AccountReference": self.reference,
                "TransactionDesc": description
            }
            
            # Log the payload (excluding sensitive fields)
            logging.info("Payload: %s", {k: v for k, v in payload.items() if k not in ['Password', 'PhoneNumber']})
            
            # Send request
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                headers=headers,
                json=payload  
            )
            
            # Log the response
            logging.info("Response Status Code: %s", response.status_code)
            logging.info("Response Text: %s", response.text)
            print("Response Status Code:", response.status_code)
            print("Response Text:", response.text)
            
            # For 400 errors, try to extract more information
            if response.status_code == 400:
                error_content = response.text
                try:
                    error_json = response.json()
                    error_message = error_json.get('errorMessage', '')
                    error_code = error_json.get('errorCode', '')
                    logging.error(f"M-Pesa API error: {error_code} - {error_message}")
                    print(f"M-Pesa API error: {error_code} - {error_message}")
                except Exception:
                    logging.error(f"Could not parse error response: {error_content}")
                    print(f"Could not parse error response: {error_content}")
            
            # Raise exception for non-200 status codes
            response.raise_for_status()
            
            # Return response JSON
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to initiate STK push: {str(e)}")
            # Get more detailed error information
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logging.error(f"API error details: {error_detail}")
                    print(f"API error details: {error_detail}")
                except Exception:
                    logging.error(f"Raw error response: {e.response.text}")
                    print(f"Raw error response: {e.response.text}")
            raise Exception(f"Failed to initiate STK push: {str(e)}")
            
    def query_transaction_status(self, checkout_request_id):
        """Query the status of an STK push transaction"""
        try:
            # Special handling for development mode
            if settings.DEBUG and checkout_request_id.startswith('ws_'):
                # In development mode, simulate a successful transaction
                logging.info(f"Development mode: Simulating transaction status for {checkout_request_id}")
                return {
                    'ResponseCode': '0',
                    'ResponseDescription': 'The service request has been accepted successfully',
                    'ResultCode': '0',
                    'ResultDesc': 'The service request is processed successfully',
                    'MerchantRequestID': f'mock-{checkout_request_id}',
                    'CheckoutRequestID': checkout_request_id,
                    'Amount': '1000',
                    'MpesaReceiptNumber': f'DEV{random.randint(1000000, 9999999)}',
                    'TransactionDate': datetime.now().strftime('%Y%m%d%H%M%S'),
                    'PhoneNumber': '254722000000'
                }
            
            # Get access token
            access_token = self.get_access_token()
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare payload
            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            # Log request details (for debugging)
            logging.info(f"Querying transaction status for: {checkout_request_id}")
            logging.debug(f"Query Status Payload: {json.dumps(payload)}")
            
            # Send request
            response = requests.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                headers=headers,
                json=payload,
                timeout=30  # Add timeout to prevent hanging
            )
            
            # Log the response
            logging.info("Query Status Response Code: %s", response.status_code)
            logging.info("Query Status Response Text: %s", response.text)
            
            # Raise exception for non-200 status codes
            response.raise_for_status()
            
            # Return response JSON
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error querying transaction status: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Response code: {e.response.status_code}")
                try:
                    logging.error(f"Response content: {e.response.text}")
                except Exception:
                    logging.error("Could not log response content")
            
            # In development mode, don't fail completely
            if settings.DEBUG:
                return {
                    'ResponseCode': '1',
                    'ResponseDescription': 'Development mode: Error querying transaction',
                    'ResultCode': '1',
                    'ResultDesc': f'Development error: {str(e)}'
                }
            raise Exception(f"Failed to query transaction status: {str(e)}")
            
        except Exception as e:
            logging.error(f"Failed to query transaction status: {str(e)}")
            # In development mode, don't fail completely
            if settings.DEBUG:
                return {
                    'ResponseCode': '1',
                    'ResponseDescription': 'Development mode: Error querying transaction',
                    'ResultCode': '1',
                    'ResultDesc': f'Development error: {str(e)}'
                }
            raise Exception(f"Failed to query transaction status: {str(e)}")
    


class PayPalService:
    """Service class for handling PayPal transactions"""
    
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.environment = settings.PAYPAL_ENVIRONMENT
        self.base_url = 'https://api-m.sandbox.paypal.com' if self.environment == 'sandbox' else 'https://api-m.paypal.com'

    def get_access_token(self):
        """Get OAuth access token from PayPal"""
        url = f"{self.base_url}/v1/oauth2/token"
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'grant_type': 'client_credentials'}
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            raise Exception(f"Failed to get PayPal access token: {str(e)}")

    def create_order(self, amount, currency='USD', intent='CAPTURE'):
        """Create a PayPal order"""
        access_token = self.get_access_token()
        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "intent": intent,
            "purchase_units": [{
                "amount": {
                    "currency_code": currency,
                    "value": str(amount)
                }
            }]
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to create PayPal order: {str(e)}")


    