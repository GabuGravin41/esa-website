from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.conf import settings
from unittest.mock import patch, MagicMock
from core.services import MpesaService
from core.models import (
    MpesaTransaction, 
    Payment,
    validate_phone_number,
    validate_mpesa_amount
)
import json
from django.contrib.auth.models import User


class MpesaServiceTest(TestCase):
    """Test cases for M-Pesa service integration"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.mpesa_service = MpesaService()
        self.test_phone = "254712345678"
        self.test_amount = 1000
        self.test_reference = "TEST123"
        self.test_description = "Test Payment"

        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test payment
        self.payment = Payment.objects.create(
            user=self.test_user,
            amount=self.test_amount,
            payment_method='mpesa',
            status='pending'
        )
        
        # Create test transaction
        self.mpesa_tx = MpesaTransaction.objects.create(
            checkout_request_id='ws_CO_123456789',
            payment=self.payment,
            phone_number=self.test_phone,
            amount=self.test_amount,
            status='pending'
        )

    @patch('requests.get')
    def test_get_access_token(self, mock_get):
        """Test getting access token from Daraja API"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test_token'}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        token = self.mpesa_service.get_access_token()
        self.assertEqual(token, 'test_token')

    
    def initiate_stk_push(self, phone_number, amount, reference, description):
        """Initiate STK Push payment"""
        try:
            # Validate inputs
            validate_phone_number(phone_number)
            validate_mpesa_amount(amount)
            if not reference:
                raise ValidationError('Reference is required')

            access_token = self.get_access_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(1),
                "PartyA": 254701606056,
                "PartyB": self.business_shortcode,
                "PhoneNumber": 254701606056,
                "CallBackURL": settings.MPESA_CALLBACK_URL,
                "AccountReference": reference,
                "TransactionDesc": description
            }
            
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers=headers
            )
            
            # Raise exception for non-200 status codes
            if response.status_code != 200:
                raise Exception(f"Failed to initiate STK push: {response.text}")
                
            result = response.json()
            if result.get('ResponseCode') != '0':
                raise Exception(f"Failed to initiate STK push: {result.get('ResponseDescription')}")
                
            return result
            
        except ValidationError as e:
            raise
        except Exception as e:
            raise Exception(f"Failed to initiate STK push: {str(e)}")
        

   

    @patch('requests.post')
    @patch('core.services.MpesaService.get_access_token')
    def test_initiate_stk_push_success(self, mock_get_token, mock_post):
        """Test successful STK push initiation"""
        # Mock the access token
        mock_get_token.return_value = 'test_token'
        
        # Mock successful STK push response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'CheckoutRequestID': 'ws_CO_123456789',
            'MerchantRequestID': 'test-merchant-123',
            'ResponseCode': '0',
            'ResponseDescription': 'Success. Request accepted for processing',
            'CustomerMessage': 'Success. Request accepted for processing'
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Initiate STK push
        response = self.mpesa_service.initiate_stk_push(
            phone_number=self.test_phone,
            amount=self.test_amount,
            reference=self.test_reference,
            description=self.test_description
        )

        # Verify the response
        self.assertEqual(response['ResponseCode'], '0')
        self.assertTrue('CheckoutRequestID' in response)
        self.assertTrue('MerchantRequestID' in response)

        # Verify the request payload
        expected_payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": self.test_amount,
            "PartyA": self.test_phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": self.test_phone,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": self.test_reference,
            "TransactionDesc": self.test_description
        }
        
        actual_payload = mock_post.call_args[1]['json']
        for key in expected_payload:
            self.assertEqual(actual_payload[key], expected_payload[key])

    @patch('requests.post')
    @patch('core.services.MpesaService.get_access_token')
    def test_initiate_stk_push_failure(self, mock_get_token, mock_post):
        """Test STK push failure scenarios"""
        mock_get_token.return_value = 'test_token'

        # Test case 1: API error response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'ResponseCode': '1',
            'ResponseDescription': 'Failed. Invalid phone number format',
        }
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_post.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.mpesa_service.initiate_stk_push(
                phone_number='254712345678',  # Use valid phone number to test API error
                amount=self.test_amount,
                reference=self.test_reference,
                description=self.test_description
            )
        self.assertTrue('Failed to initiate STK push' in str(context.exception))

        # Test case 2: Network error
        mock_post.side_effect = requests.exceptions.RequestException('Network error')
        
        with self.assertRaises(Exception) as context:
            self.mpesa_service.initiate_stk_push(
                phone_number=self.test_phone,
                amount=self.test_amount,
                reference=self.test_reference,
                description=self.test_description
            )
        self.assertTrue('Failed to initiate STK push' in str(context.exception))

        # Test case 3: Validation error
        with self.assertRaises(ValidationError):
            self.mpesa_service.initiate_stk_push(
                phone_number='invalid_phone',
                amount=self.test_amount,
                reference=self.test_reference,
                description=self.test_description
            )
        
    
    
    @patch('requests.post')
    @patch('requests.post')
    @patch('core.services.MpesaService.get_access_token')
    def test_initiate_stk_push_validation(self, mock_get_token, mock_post):
        """Test STK push input validation"""
        mock_get_token.return_value = 'test_token'
        
        # Test invalid phone numbers
        invalid_phones = [
            'invalid',       # Wrong format
            '712345678',    # Missing country code
            '254612345678', # Invalid prefix
            '25471234567',  # Too short
            None,           # None value
            ''             # Empty string
        ]
        
        for phone in invalid_phones:
            with self.assertRaises(
                ValidationError, 
                msg=f"ValidationError not raised for invalid phone: {phone}"
            ):
                self.mpesa_service.initiate_stk_push(
                    phone_number=phone,
                    amount=self.test_amount,
                    reference=self.test_reference,
                    description=self.test_description
                )

        # Test invalid amounts
        invalid_amounts = [
            -100,     # Negative
            0,        # Zero
            1.5,      # Decimal
            200000,   # Too large
            None,     # None value
            'abc'     # Non-numeric
        ]
        
        for amount in invalid_amounts:
            with self.assertRaises(
                ValidationError,
                msg=f"ValidationError not raised for invalid amount: {amount}"
            ):
                self.mpesa_service.initiate_stk_push(
                    phone_number=self.test_phone,
                    amount=amount,
                    reference=self.test_reference,
                    description=self.test_description
                )

        # Test invalid reference
        invalid_refs = [None, '', '   ']
        for ref in invalid_refs:
            with self.assertRaises(
                ValidationError,
                msg=f"ValidationError not raised for invalid reference: {ref}"
            ):
                self.mpesa_service.initiate_stk_push(
                    phone_number=self.test_phone,
                    amount=self.test_amount,
                    reference=ref,
                    description=self.test_description
                )





class MpesaValidationTest(TestCase):
    """Test cases for M-Pesa validation functions"""

    def test_phone_number_validation(self):
        """Test phone number validation"""
        invalid_numbers = [
            '0712345678',      # Missing country code
            '254612345678',    # Invalid prefix (must start with 254 followed by 7 or 1)
            '25471234567',     # Too short
            '2547123456789',   # Too long
            '254abc45678',     # Non-numeric
            '254712345abc',    # Contains letters
            None,              # None value
            '',               # Empty string
            '   ',           # Whitespace
            '254001234567'   # Invalid prefix after 254
        ]
        
        # Test invalid numbers
        for number in invalid_numbers:
            try:
                validate_phone_number(number)
                self.fail(f'ValidationError not raised for invalid number: {number}')
            except ValidationError:
                pass  # Test passes if ValidationError is raised


        # Test valid numbers
        valid_numbers = [
            '254701606056',  # Valid Safaricom
            '254123456789'   # Valid format
        ]
        
        for number in valid_numbers:
            try:
                result = validate_phone_number(number)
                self.assertEqual(result, number)
            except ValidationError:
                self.fail(f'ValidationError raised for valid number: {number}')

        
    
    def test_amount_validation(self):
        """Test amount validation"""
        invalid_amounts = [
            0,              # Zero amount
            -100,          # Negative amount
            1.5,           # Decimal amount
            250000,        # Amount too large
            'abc',         # Non-numeric
            None,          # None value
        ]
        
        for amount in invalid_amounts:
            with self.assertRaises(ValidationError):
                validate_mpesa_amount(amount)

        # Test valid amounts
        valid_amounts = [100, 1000, 150000]
        for amount in valid_amounts:
            result = validate_mpesa_amount(amount)
            self.assertEqual(result, amount)


mpesa_service = MpesaService()
response = mpesa_service.initiate_stk_push(
    phone_number='254701606056',  # Replace with your phone number
    amount=1,  # Amount in KES
    reference='TestRef123',  # Reference for the transaction
    description='Test Payment'  # Description of the transaction
)

print(response)
