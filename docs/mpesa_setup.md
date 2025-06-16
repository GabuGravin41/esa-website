# M-Pesa Integration Guide for ESA-KU Website

This comprehensive guide outlines the steps to properly set up and test M-Pesa payments for the ESA-KU website.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Registering for Daraja API Access](#registering-for-daraja-api-access)
3. [Obtaining API Credentials](#obtaining-api-credentials)
4. [Setting Up Environment Variables](#setting-up-environment-variables)
5. [Configuring Callback URLs](#configuring-callback-urls)
6. [Testing in Sandbox Environment](#testing-in-sandbox-environment)
7. [Going Live with Production Credentials](#going-live-with-production-credentials)
8. [Troubleshooting Common Issues](#troubleshooting-common-issues)
9. [Best Practices for M-Pesa Integration](#best-practices-for-m-pesa-integration)
10. [Support Resources](#support-resources)

## Prerequisites

1. A Safaricom business account with Lipa Na M-Pesa (Buy Goods or Paybill) capability
   - For a Paybill, you must have a registered business and apply through Safaricom
   - For a Till Number (Buy Goods), you can apply at any Safaricom shop with your business registration documents
   
2. Access to the Safaricom Developer Portal: [https://developer.safaricom.co.ke/](https://developer.safaricom.co.ke/)

3. Your ESA-KU website must be accessible via HTTPS for secure callbacks

## Registering for Daraja API Access

1. Visit [https://developer.safaricom.co.ke/](https://developer.safaricom.co.ke/) and click "Sign Up"
2. Fill in your details to create a developer account
3. Verify your email address by clicking the link sent to your email
4. Log in to the Developer Portal with your credentials
5. Navigate to "My Apps" section
6. Click "Add a New App"
7. Fill in the app details:
   - App Name: "ESA-KU Payments"
   - Description: "Payment processing for Engineering Students Association at Kenyatta University"
   - Select the following APIs:
     - M-Pesa Express (STK Push)
     - M-Pesa Query

## Obtaining API Credentials

After creating your app, you'll receive:

1. **Consumer Key**: A unique identifier for your application
2. **Consumer Secret**: A secret key used to authenticate your application
3. **Test Credentials for the Sandbox Environment**:
   - Test Shortcode (usually 174379 for sandbox)
   - Test Passkey

To get production credentials:
1. Go to "Production" tab in your app
2. Click "Go Live" button
3. Complete the application form with your business details
4. Upload required documents (business registration, Safaricom contract, etc.)
5. Wait for Safaricom to approve your request (can take 1-7 business days)

## Setting Up Environment Variables

Add the following variables to your `.env` file at the root of your project:

```
# M-Pesa Daraja API Settings - SANDBOX
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=your_sandbox_consumer_key_here
MPESA_CONSUMER_SECRET=your_sandbox_consumer_secret_here
MPESA_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
MPESA_CALLBACK_URL=https://your-site.com/mpesa/callback/
MPESA_REFERENCE=ESA-KU

# For production, you would use:
# MPESA_ENVIRONMENT=production
# MPESA_CONSUMER_KEY=your_production_consumer_key_here
# MPESA_CONSUMER_SECRET=your_production_consumer_secret_here
# MPESA_SHORTCODE=your_actual_paybill_or_till_number
# MPESA_PASSKEY=your_production_passkey_from_safaricom
```

## Configuring Callback URLs

M-Pesa will send payment notifications to your callback URL. This URL:

1. Must be publicly accessible (not localhost)
2. Must use HTTPS protocol for security
3. Should point to your `mpesa_callback` view

### Setting Up the Callback URL:

1. For testing, use a service like ngrok to expose your local development server:
   ```bash
   ngrok http 8000
   ```
   This gives you a temporary public URL like `https://abc123.ngrok.io`

2. Update your `.env` file with this URL:
   ```
   MPESA_CALLBACK_URL=https://abc123.ngrok.io/membership/payment/mpesa/callback/
   ```

3. For production, use your actual domain:
   ```
   MPESA_CALLBACK_URL=https://esa-ku.org/membership/payment/mpesa/callback/
   ```

## Testing in Sandbox Environment

1. Make sure your `.env` file has the sandbox settings:
   ```
   MPESA_ENVIRONMENT=sandbox
   ```

2. Use the following test phone numbers for sandbox:
   - `254708374149` (Accepts STK push and completes payment)
   - `254700000000` (Declines STK push)

3. Test amounts:
   - Any amount above 0 should work
   - For testing specific scenarios, refer to Safaricom's developer documentation

4. When testing, make sure to check both successful and failed payment scenarios

## Going Live with Production Credentials

Once your sandbox testing is complete and your "Go Live" request is approved:

1. Update your `.env` file with production credentials:
   ```
   MPESA_ENVIRONMENT=production
   MPESA_CONSUMER_KEY=your_production_consumer_key
   MPESA_CONSUMER_SECRET=your_production_consumer_secret
   MPESA_SHORTCODE=your_actual_paybill_or_till_number
   MPESA_PASSKEY=your_production_passkey
   ```

2. Update your callback URL to use your production domain:
   ```
   MPESA_CALLBACK_URL=https://esa-ku.org/membership/payment/mpesa/callback/
   ```

3. Perform a real test transaction with a small amount (e.g., KSh 1) to verify everything works in production

## Troubleshooting Common Issues

### STK Push Not Working
- **Invalid phone number format**: Ensure phone numbers start with "254" (country code for Kenya) and are 12 digits
- **Wrong credentials**: Double-check your consumer key and consumer secret
- **Incorrect shortcode**: Verify your business shortcode is correct
- **Invalid passkey**: Ensure your passkey is correct and properly formatted
- **Amount too small**: The minimum amount is KSh 1

### Callback Not Received
- **Inaccessible URL**: Make sure your callback URL is publicly accessible
- **Wrong URL format**: The URL must start with https://
- **Server issues**: Check if your server is accepting POST requests
- **Firewall blocking**: Ensure your firewall allows incoming connections from Safaricom IPs

### Transaction Failed
- **Insufficient funds**: The user may not have enough money in their M-Pesa account
- **Canceled by user**: The user might have declined the STK push
- **Timeout**: The user might not have responded to the prompt in time
- **Wrong PIN**: The user might have entered the wrong M-Pesa PIN multiple times

## Best Practices for M-Pesa Integration

1. **Environment Management**:
   - Keep development, staging, and production environments separate
   - Never use production credentials in development

2. **Security**:
   - Store API credentials securely in environment variables
   - Never expose credentials in client-side code
   - Implement HTTPS for all communication

3. **Validation**:
   - Always validate phone numbers before initiating STK push
   - Verify transaction details in callbacks before marking payments as complete

4. **Error Handling**:
   - Implement comprehensive error handling for all API calls
   - Log all transaction attempts and responses for troubleshooting
   - Create user-friendly error messages

5. **Transaction Management**:
   - Generate unique transaction references
   - Use database transactions to ensure payment records are consistent
   - Implement retries for failed network requests

6. **Testing**:
   - Test with different amounts
   - Test with different phone numbers
   - Test timeouts and cancellations

7. **User Experience**:
   - Provide clear instructions for users
   - Show appropriate loading states during payment processing
   - Send confirmation messages or emails after successful payments

## Support Resources

- **Safaricom Developer Support**: developers@safaricom.co.ke
- **Daraja API Documentation**: [https://developer.safaricom.co.ke/Documentation](https://developer.safaricom.co.ke/Documentation)
- **M-Pesa Express (STK Push) API Documentation**: [https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate](https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate)
- **Safaricom Developer Community**: [https://developer.safaricom.co.ke/forum](https://developer.safaricom.co.ke/forum)

---

## Implementation Checklist for ESA-KU Website

- [ ] Register on Safaricom Developer Portal
- [ ] Create app and get sandbox credentials
- [ ] Set up environment variables in `.env` file
- [ ] Configure callback URL
- [ ] Test payments in sandbox environment
- [ ] Apply for production credentials
- [ ] Update to production credentials when approved
- [ ] Perform final testing with real transactions
- [ ] Document the payment flow for future maintenance

For any internal questions about this implementation, please contact the ESA-KU technical team at tech@esa-ku.org.
