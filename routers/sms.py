import os
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning
from fastapi import APIRouter
from dotenv import load_dotenv

load_dotenv()

# Suppress the warning that Python throws when we bypass SSL verification
warnings.simplefilter('ignore', InsecureRequestWarning)

router = APIRouter()

def send_sms(phone_number: str, message: str) -> bool:
    """Helper function to send SMS via direct REST API to bypass SSL errors."""
    url = "https://api.sandbox.africastalking.com/version1/messaging"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "apiKey": os.getenv("AT_API_KEY")
    }
    payload = {
        "username": os.getenv("AT_USERNAME"),
        "to": phone_number,
        "message": message
    }
    
    try:
        # verify=False is the magic key that bypasses the local SSL mismatch
        response = requests.post(url, data=payload, headers=headers, verify=False)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"HTTP Request failed for {phone_number}: {e}")
        return False

def dispatch_logistics_alerts(seller_phone: str, buyer_phone: str, delivery_fee: float, pickup_otp: str, dropoff_otp: str):
    """Blasts the necessary SMS alerts when a job is escrowed."""
    
    # 1. Alert the Seller
    seller_message = (
        f"MzigoSafe: Funds Secured! "
        f"A rider is being dispatched. Your Pickup OTP is {pickup_otp}. "
        f"Give this to the rider when they collect the package."
    )
    if send_sms(seller_phone, seller_message):
        print(f"SMS Success: Pickup OTP sent to Seller ({seller_phone})")
    else:
        print("Failed to send Seller SMS")

    # 2. Alert the Buyer
    buyer_message = (
        f"MzigoSafe: Escrow locked! "
        f"Your Delivery OTP is {dropoff_otp}. "
        f"ONLY give this to the rider when they hand you the package."
    )
    if send_sms(buyer_phone, buyer_message):
        print(f"SMS Success: Dropoff OTP sent to Buyer ({buyer_phone})")
    else:
        print("Failed to send Buyer SMS")

    # 3. Alert the Rider (Broadcast)
    test_rider_phone = "+254733333333" 
    
    rider_message = (
        f"MzigoSafe Alert! New job available. "
        f"Earn KES {delivery_fee}. "
        f"Dial *384*4798# to accept." 
    )
    if send_sms(test_rider_phone, rider_message):
        print(f"SMS Success: Broadcast sent to Rider ({test_rider_phone})")
    else:
        print("Failed to send Rider Broadcast")