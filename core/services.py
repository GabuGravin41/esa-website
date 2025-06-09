# import base64
# import json
# import requests
# from datetime import datetime
# from django.conf import settings
# from django.utils import timezone
# from decimal import Decimal

# class MpesaService:
#     """Service class for handling M-Pesa transactions"""
    
#     def __init__(self):
#         self.consumer_key = settings.MPESA_CONSUMER_KEY
#         self.consumer_secret = settings.MPESA_CONSUMER_SECRET
#         self.shortcode = settings.MPESA_SHORTCODE
#         self.passkey = settings.MPESA_PASSKEY
#         self.callback_url = settings.MPESA_CALLBACK_URL
#         self.base_url = "https://sandbox.safaricom.co.ke" if settings.DEBUG else "https://api.safaricom.co.ke"
        
#     def get_access_token(self):
#         """Get OAuth access token from M-Pesa"""
#         auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
#         headers = {
#             "Authorization": f"Basic {auth}"
#         }
#         response = requests.get(f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials", headers=headers)
#         return response.json().get("access_token")
    
#     def initiate_stk_push(self, phone_number, amount, reference, description):
#         """Initiate STK push for payment"""
#         access_token = self.get_access_token()
#         timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#         password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        
#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json"
#         }
        
#         payload = {
#             "BusinessShortCode": self.shortcode,
#             "Password": password,
#             "Timestamp": timestamp,
#             "TransactionType": "CustomerPayBillOnline",
#             "Amount": int(amount),
#             "PartyA": phone_number,
#             "PartyB": self.shortcode,
#             "PhoneNumber": phone_number,
#             "CallBackURL": self.callback_url,
#             "AccountReference": reference,
#             "TransactionDesc": description
#         }
        
#         response = requests.post(
#             f"{self.base_url}/mpesa/stkpush/v1/processrequest",
#             headers=headers,
#             json=payload
#         )
#         return response.json()
    
#     def query_transaction_status(self, checkout_request_id):
#         """Query the status of a transaction"""
#         access_token = self.get_access_token()
#         timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#         password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        
#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json"
#         }
        
#         payload = {
#             "BusinessShortCode": self.shortcode,
#             "Password": password,
#             "Timestamp": timestamp,
#             "CheckoutRequestID": checkout_request_id
#         }
        
#         response = requests.post(
#             f"{self.base_url}/mpesa/stkpushquery/v1/query",
#             headers=headers,
#             json=payload
#         )
#         return response.json()

# class PayPalService:
#     """Service class for handling PayPal transactions"""
    
#     def __init__(self):
#         self.client_id = settings.PAYPAL_CLIENT_ID
#         self.client_secret = settings.PAYPAL_SECRET
#         self.mode = settings.PAYPAL_MODE
#         self.base_url = "https://api-m.sandbox.paypal.com" if self.mode == "sandbox" else "https://api-m.paypal.com"
    
#     def get_access_token(self):
#         """Get OAuth access token from PayPal"""
#         auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
#         headers = {
#             "Authorization": f"Basic {auth}",
#             "Content-Type": "application/x-www-form-urlencoded"
#         }
#         data = "grant_type=client_credentials"
#         response = requests.post(f"{self.base_url}/v1/oauth2/token", headers=headers, data=data)
#         return response.json().get("access_token")
    
#     def create_order(self, amount, currency, reference, return_url, cancel_url):
#         """Create a PayPal order"""
#         access_token = self.get_access_token()
#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json",
#             "Prefer": "return=representation"
#         }
        
#         payload = {
#             "intent": "CAPTURE",
#             "purchase_units": [{
#                 "reference_id": reference,
#                 "amount": {
#                     "currency_code": currency,
#                     "value": str(amount)
#                 }
#             }],
#             "application_context": {
#                 "return_url": return_url,
#                 "cancel_url": cancel_url
#             }
#         }
        
#         response = requests.post(
#             f"{self.base_url}/v2/checkout/orders",
#             headers=headers,
#             json=payload
#         )
#         return response.json()
    
#     def capture_order(self, order_id):
#         """Capture a PayPal order"""
#         access_token = self.get_access_token()
#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json",
#             "Prefer": "return=representation"
#         }
        
#         response = requests.post(
#             f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
#             headers=headers
#         )
#         return response.json() 






import requests
import base64
from datetime import datetime
from django.conf import settings

# class MpesaService:
#     def __init__(self):
#         self.business_shortcode = settings.MPESA_SHORTCODE
#         self.passkey = settings.MPESA_PASSKEY
#         self.consumer_key = settings.MPESA_CONSUMER_KEY
#         self.consumer_secret = settings.MPESA_CONSUMER_SECRET
#         self.environment = settings.MPESA_ENVIRONMENT
#         self.callback_url = settings.MPESA_CALLBACK_URL
#         self.reference = settings.MPESA_REFERENCE
#         self.base_url = 'https://sandbox.safaricom.co.ke' if self.environment == 'sandbox' else 'https://api.safaricom.co.ke'

#     def get_access_token(self):
#         url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
#         auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
#         headers = {'Authorization': f'Basic {auth}'}
        
#         try:
#             response = requests.get(url, headers=headers)
#             response.raise_for_status()
#             return response.json()['access_token']
#         except Exception as e:
#             raise Exception(f"Failed to get access token: {str(e)}")

#     def initiate_stk_push(self, phone_number, amount, reference, description):
#         """Initiate STK push for payment"""
#         try:
#             # Get access token
#             access_token = self.get_access_token()
            
#             # Generate timestamp and password
#             timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
#             password = base64.b64encode(
#                 f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
#             ).decode()
            
#             # Set headers
#             headers = {
#                 'Authorization': f'Bearer {access_token}',
#                 'Content-Type': 'application/json'
#             }
            
#             # Prepare payload
#             payload = {
#                 "BusinessShortCode": self.business_shortcode,
#                 "Password": password,
#                 "Timestamp": timestamp,
#                 "TransactionType": "CustomerPayBillOnline",
#                 "Amount": int(amount),
#                 "PartyA": phone_number,
#                 "PartyB": self.business_shortcode,
#                 "PhoneNumber": phone_number,
#                 "CallBackURL": self.callback_url,
#                 "AccountReference": reference,
#                 "TransactionDesc": description
#             }
            
#             # Log the payload
#             print("Payload:", payload)
            
#             # Send request
#             response = requests.post(
#                 f"{self.base_url}/mpesa/stkpush/v1/processrequest",
#                 headers=headers,
#                 json=payload  
#             )
            
#             # Log the response
#             print("Response Status Code:", response.status_code)
#             print("Response Text:", response.text)
            
#             # Raise exception for non-200 status codes
#             response.raise_for_status()
            
#             # Return response JSON
#             return response.json()
        
#         except requests.exceptions.RequestException as e:
#             raise Exception(f"Failed to initiate STK push: {str(e)}")
    



class MpesaService:
    def __init__(self):
        self.business_shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.environment = settings.MPESA_ENVIRONMENT
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.reference = settings.MPESA_REFERENCE
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
            print("Response Status Code:", response.status_code)
            print("Response Text:", response.text)
            
            # Raise exception for non-200 status codes
            response.raise_for_status()
            
            # Return response JSON
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to initiate STK push: {str(e)}")
    


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


    