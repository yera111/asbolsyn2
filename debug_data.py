import datetime
import pytz
from decimal import Decimal

# Test timezone logic
def test_timezone_logic():
    print('=== TIMEZONE LOGIC TEST ===')
    
    # Simulate Almaty timezone (UTC+5)
    ALMATY_TIMEZONE = pytz.FixedOffset(5 * 60)  # 5 hours * 60 minutes
    
    def get_current_almaty_time():
        return datetime.datetime.now(ALMATY_TIMEZONE)
    
    # Test current time
    current_time = get_current_almaty_time()
    print(f'Current Almaty time: {current_time}')
    
    # Test meal pickup times (simulating different scenarios)
    test_cases = [
        # Case 1: Meal that should be active (ends in 2 hours)
        current_time + datetime.timedelta(hours=2),
        # Case 2: Meal that should be expired (ended 1 hour ago)
        current_time - datetime.timedelta(hours=1),
        # Case 3: Meal that ends in 30 minutes
        current_time + datetime.timedelta(minutes=30),
        # Case 4: Meal that ended 5 minutes ago
        current_time - datetime.timedelta(minutes=5),
    ]
    
    for i, pickup_end_time in enumerate(test_cases, 1):
        print(f'\nTest Case {i}:')
        print(f'  Pickup end time: {pickup_end_time}')
        print(f'  Current time: {current_time}')
        
        # Test the filtering logic from browse_meals
        if pickup_end_time.tzinfo is None:
            # If naive datetime, assume it's in Almaty timezone
            pickup_end_time_tz = pickup_end_time.replace(tzinfo=ALMATY_TIMEZONE)
        else:
            # Convert to Almaty timezone
            pickup_end_time_tz = pickup_end_time.astimezone(ALMATY_TIMEZONE)
        
        is_active = pickup_end_time_tz > current_time
        print(f'  Should be active: {is_active}')
        print(f'  Time difference: {pickup_end_time_tz - current_time}')

def test_earnings_calculation():
    print('\n=== EARNINGS CALCULATION TEST ===')
    
    # Test earnings calculation logic
    meal_price = Decimal('1500.00')  # 1500 tenge
    quantity = 2
    commission_rate = Decimal('0.15')  # 15%
    
    gross_amount = meal_price * quantity
    commission_amount = gross_amount * commission_rate
    net_amount = gross_amount - commission_amount
    
    print(f'Meal price: {meal_price} tenge')
    print(f'Quantity: {quantity}')
    print(f'Gross amount: {gross_amount} tenge')
    print(f'Commission rate: {commission_rate * 100}%')
    print(f'Commission amount: {commission_amount} tenge')
    print(f'Net amount (vendor earnings): {net_amount} tenge')
    
    # Test case where vendor should have earned 750 tenge
    print(f'\nTest case for 750 tenge earnings:')
    if net_amount == Decimal('750.00'):
        print('✓ This matches the expected 750 tenge!')
    else:
        # Calculate what the original order might have been
        target_net = Decimal('750.00')
        target_gross = target_net / (1 - commission_rate)
        print(f'To get 750 tenge net, gross should be: {target_gross} tenge')
        print(f'With 15% commission: {target_gross * commission_rate} tenge commission')

if __name__ == "__main__":
    test_timezone_logic()
    test_earnings_calculation() 