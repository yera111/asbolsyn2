# End-to-End Testing Guide for As Bolsyn Bot

This guide provides detailed instructions for performing end-to-end testing of the As Bolsyn Telegram bot in a production environment.

## Prerequisites

Before beginning the testing process, ensure you have:

1. **Access to the deployed bot** on Render or another PaaS provider
2. **Two separate Telegram accounts**:
   - One for testing vendor functionality
   - One for testing consumer functionality
3. **Admin access** to the bot for approving vendors
4. **Test payment cards/credentials** for simulating payments

## Setting Up the Test Environment

1. **Prepare test accounts**:
   ```bash
   # Run the test data setup script
   python scripts/setup_test_data.py
   ```

   This will generate test configuration files and guide you through the setup process.

2. **Verify deployment is operational**:
   - Send the `/start` command to the bot using both test accounts
   - Ensure you receive welcome messages and see the main menu

## Test Scenarios

The end-to-end testing covers the complete user flow from vendor registration to consumer purchase. Run the test script to guide you through each step:

```bash
# Run the end-to-end test script
python scripts/e2e_test.py
```

The script will guide you through the following test flows:

### 1. Vendor Registration and Meal Creation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1.1 | Start bot as vendor | Vendor receives welcome message with main menu |
| 1.2 | Register as vendor | Bot guides through registration, confirms submission |
| 1.3 | Admin receives notification | Admin can approve the vendor |
| 1.4 | Vendor receives approval | Notification about approved status |
| 1.5 | Vendor creates meal | Bot guides through meal creation with validation |
| 1.6 | Vendor views meals | New meal appears in vendor's meal list |

### 2. Consumer Browse and Purchase

| Step | Action | Expected Result |
|------|--------|-----------------|
| 2.1 | Start bot as consumer | Consumer receives welcome message with main menu |
| 2.2 | Browse available meals | Consumer sees list of meals including test meal |
| 2.3 | View meal details | Consumer sees detailed meal information |
| 2.4 | Select meal portions | Consumer can select portions and see total price |
| 2.5 | Initiate purchase | Consumer receives payment link |
| 2.6 | Complete test payment | Payment is processed |
| 2.7 | Receive confirmation | Consumer gets order confirmation with details |

### 3. Order Notifications and History

| Step | Action | Expected Result |
|------|--------|-----------------|
| 3.1 | Vendor gets order notification | Vendor is notified about the new order |
| 3.2 | Consumer checks order history | Order appears in consumer's order history |
| 3.3 | Vendor checks order history | Order appears in vendor's order history |

### 4. Nearby Meals Functionality

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.1 | Consumer tests nearby meals | Bot shows meals based on consumer's location |

### 5. Vendor Meal Management

| Step | Action | Expected Result |
|------|--------|-----------------|
| 5.1 | Vendor deletes meal | Meal is successfully removed from active meals |

## Testing Checklist

During testing, pay particular attention to:

- **Russian language**: All bot messages should be in Russian
- **Data validation**: Bot should validate input data and provide appropriate error messages
- **Database updates**: Check that changes are correctly saved to the database
- **Payment flow**: Verify payment integration works correctly with test credentials
- **Notifications**: Ensure both vendor and consumer receive appropriate notifications
- **Error handling**: Test error scenarios (e.g., invalid inputs, unavailable meals)

## Test Reporting

The e2e_test.py script generates a log file with the test results. Review this file to identify any issues encountered during testing.

## Troubleshooting Common Issues

### Payment Gateway Issues

If payment testing fails:
1. Verify the payment gateway environment variables are correctly set
2. Confirm test payment credentials are valid
3. Check the payment gateway logs for any error messages

### Webhook Issues

If messages are delayed or not delivered:
1. Verify the webhook is properly configured
2. Check the logs on your PaaS provider for any webhook errors
3. Ensure your application is handling Telegram updates correctly

### Database Issues

If data is not persisting correctly:
1. Verify database connection parameters
2. Check database permissions
3. Examine application logs for database-related errors

## Production Validation Checklist

Before considering the deployment successful, verify:

✅ Vendor registration works correctly  
✅ Admin approval process functions properly  
✅ Vendors can add, view, and delete meals  
✅ Consumers can browse and view meals  
✅ Nearby meal search functions correctly  
✅ Payment gateway integration is working  
✅ Order notifications are delivered to both parties  
✅ All messages and UI elements are in Russian  
✅ Error handling is robust and user-friendly  

## Conclusion

The end-to-end testing validates the complete functionality of the As Bolsyn bot in a production environment. This ensures that all components work together properly and the bot is ready for real users. 