#!/usr/bin/env python
"""
Test Data Setup Script for As Bolsyn Bot

This script helps you prepare test data for conducting end-to-end tests of the As Bolsyn bot.
It creates a checklist of items that need to be set up before running the end-to-end tests.

Usage:
- Run this script before conducting end-to-end tests
- Follow the prompts to verify you have all necessary test accounts and credentials
- Use the generated IDs and information in your testing
"""

import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"test_setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
CONFIG_FILE = "test_config.json"
DEFAULT_CONFIG = {
    "bot_username": "@your_bot_username",
    "admin_chat_id": "your_admin_chat_id",
    "test_accounts": {
        "vendor": {
            "username": "@test_vendor_username",
            "chat_id": "",
            "name": "Test Café Almaty",
            "phone": "+7123456789"
        },
        "consumer": {
            "username": "@test_consumer_username",
            "chat_id": ""
        }
    },
    "payment_gateway": {
        "test_card": "4111 1111 1111 1111",
        "test_expiry": "12/25",
        "test_cvv": "123",
        "test_3ds_password": "password"
    },
    "almaty_test_locations": [
        {"name": "Central Almaty", "latitude": 43.238949, "longitude": 76.889709},
        {"name": "Mega Alma-Ata", "latitude": 43.2220, "longitude": 76.8513}
    ]
}


def load_or_create_config():
    """Load existing config or create a new one if it doesn't exist"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded existing configuration from {CONFIG_FILE}")
                return config
        except json.JSONDecodeError:
            logger.error(f"Error parsing {CONFIG_FILE}, creating new configuration")
    
    # Create new config if not exists or invalid
    with open(CONFIG_FILE, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
        logger.info(f"Created new configuration file: {CONFIG_FILE}")
    
    return DEFAULT_CONFIG


def update_config(config):
    """Save updated configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
        logger.info(f"Updated configuration in {CONFIG_FILE}")


def verify_bot_config(config):
    """Verify bot configuration"""
    print("\n=== BOT CONFIGURATION ===")
    
    bot_username = input(f"Enter bot username [{config['bot_username']}]: ")
    if bot_username:
        config['bot_username'] = bot_username
    
    admin_chat_id = input(f"Enter admin chat ID [{config['admin_chat_id']}]: ")
    if admin_chat_id:
        config['admin_chat_id'] = admin_chat_id
    
    print(f"\nBot Username: {config['bot_username']}")
    print(f"Admin Chat ID: {config['admin_chat_id']}")
    
    return config


def verify_test_accounts(config):
    """Verify test accounts"""
    print("\n=== TEST ACCOUNTS ===")
    
    # Vendor account
    print("\nVENDOR TEST ACCOUNT:")
    vendor = config['test_accounts']['vendor']
    
    vendor_username = input(f"Enter vendor test username [{vendor['username']}]: ")
    if vendor_username:
        vendor['username'] = vendor_username
    
    vendor_chat_id = input(f"Enter vendor chat ID [{vendor['chat_id']}]: ")
    if vendor_chat_id:
        vendor['chat_id'] = vendor_chat_id
    
    vendor_name = input(f"Enter vendor test name [{vendor['name']}]: ")
    if vendor_name:
        vendor['name'] = vendor_name
    
    vendor_phone = input(f"Enter vendor test phone [{vendor['phone']}]: ")
    if vendor_phone:
        vendor['phone'] = vendor_phone
    
    # Consumer account
    print("\nCONSUMER TEST ACCOUNT:")
    consumer = config['test_accounts']['consumer']
    
    consumer_username = input(f"Enter consumer test username [{consumer['username']}]: ")
    if consumer_username:
        consumer['username'] = consumer_username
    
    consumer_chat_id = input(f"Enter consumer chat ID [{consumer['chat_id']}]: ")
    if consumer_chat_id:
        consumer['chat_id'] = consumer_chat_id
    
    return config


def verify_payment_config(config):
    """Verify payment gateway test credentials"""
    print("\n=== PAYMENT GATEWAY TEST CREDENTIALS ===")
    
    payment = config['payment_gateway']
    
    test_card = input(f"Enter test card number [{payment['test_card']}]: ")
    if test_card:
        payment['test_card'] = test_card
    
    test_expiry = input(f"Enter test card expiry [{payment['test_expiry']}]: ")
    if test_expiry:
        payment['test_expiry'] = test_expiry
    
    test_cvv = input(f"Enter test CVV [{payment['test_cvv']}]: ")
    if test_cvv:
        payment['test_cvv'] = test_cvv
    
    test_3ds = input(f"Enter test 3DS password if needed [{payment.get('test_3ds_password', '')}]: ")
    if test_3ds:
        payment['test_3ds_password'] = test_3ds
    
    return config


def verify_test_locations(config):
    """Verify test locations in Almaty"""
    print("\n=== TEST LOCATIONS IN ALMATY ===")
    
    for i, location in enumerate(config['almaty_test_locations']):
        print(f"\nLocation {i+1}: {location['name']}")
        print(f"Coordinates: {location['latitude']}, {location['longitude']}")
    
    if input("\nAdd a new test location? (y/n): ").lower() == 'y':
        name = input("Enter location name: ")
        try:
            lat = float(input("Enter latitude: "))
            lng = float(input("Enter longitude: "))
            
            config['almaty_test_locations'].append({
                "name": name,
                "latitude": lat,
                "longitude": lng
            })
            
            print(f"Added new location: {name} ({lat}, {lng})")
        except ValueError:
            print("Invalid coordinates. Location not added.")
    
    return config


def generate_test_guide(config):
    """Generate test guide with the configuration"""
    print("\n=== TEST GUIDE ===")
    print("Use the following information for your end-to-end testing:")
    
    print(f"\n1. Bot: {config['bot_username']}")
    print(f"2. Admin Chat ID: {config['admin_chat_id']}")
    
    vendor = config['test_accounts']['vendor']
    print(f"\n3. Vendor Account: {vendor['username']}")
    print(f"   - Chat ID: {vendor['chat_id']}")
    print(f"   - Test Name: {vendor['name']}")
    print(f"   - Test Phone: {vendor['phone']}")
    
    consumer = config['test_accounts']['consumer']
    print(f"\n4. Consumer Account: {consumer['username']}")
    print(f"   - Chat ID: {consumer['chat_id']}")
    
    payment = config['payment_gateway']
    print(f"\n5. Payment Test Data:")
    print(f"   - Test Card: {payment['test_card']}")
    print(f"   - Expiry: {payment['test_expiry']}")
    print(f"   - CVV: {payment['test_cvv']}")
    if payment.get('test_3ds_password'):
        print(f"   - 3DS Password: {payment['test_3ds_password']}")
    
    print("\n6. Test Locations:")
    for i, location in enumerate(config['almaty_test_locations']):
        print(f"   {i+1}. {location['name']}: {location['latitude']}, {location['longitude']}")
    
    print("\nUse 'scripts/e2e_test.py' to run through the end-to-end test scenarios.")


def generate_e2e_test_config(config):
    """Generate a configuration file specifically for e2e testing"""
    e2e_config = {
        "bot_username": config['bot_username'],
        "vendor_test_name": config['test_accounts']['vendor']['name'],
        "vendor_test_phone": config['test_accounts']['vendor']['phone'],
        "meal_test_name": "Test Leftover Pilov",
        "meal_test_description": "Delicious Uzbek pilov with beef and carrots",
        "meal_test_price": "1000",
        "meal_test_quantity": "3",
        "meal_test_pickup_start": "18:00",
        "meal_test_pickup_end": "20:00",
        "meal_test_address": "Abay Avenue 150, Almaty",
        "test_location": config['almaty_test_locations'][0]
    }
    
    with open("e2e_test_config.json", 'w') as f:
        json.dump(e2e_config, f, indent=2)
        logger.info("Generated e2e test configuration in e2e_test_config.json")
    
    print("\nGenerated e2e_test_config.json with test parameters for end-to-end testing")


def main():
    """Main function to run the verification process"""
    print("=== AS BOLSYN TEST DATA SETUP ===")
    print("This script will help you prepare for end-to-end testing.")
    print("Follow the prompts to verify your test data.")
    
    config = load_or_create_config()
    
    config = verify_bot_config(config)
    config = verify_test_accounts(config)
    config = verify_payment_config(config)
    config = verify_test_locations(config)
    
    update_config(config)
    
    generate_test_guide(config)
    generate_e2e_test_config(config)
    
    print("\nSetup complete! You're ready to run end-to-end tests.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup aborted by user.")
    except Exception as e:
        logger.error(f"Error in setup: {e}")
        print(f"\nAn error occurred: {e}")
        print("Please check the log file for details.") 