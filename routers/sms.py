import os
import random
import africastalking
from fastapi import APIRouter
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Initialize Africa's Talking SDK
africastalking.initialize(
    os.getenv("AT_USERNAME"), 
    os.getenv("AT_API_KEY")
)
sms = africastalking.SMS

def generate_otp() -> str:
    return str(random.randint(1000, 9999))

def dispatch_escrow_success_alerts(buyer_phone: str, delivery_id: int, delivery_fee: float, otp: str):
    """Sends OTP to the buyer and alerts nearby riders."""
    
    buyer_message = (
        f"MzigoSafe: Funds secured! "
        f"Your delivery OTP is {otp}. "
        f"ONLY give this to the rider when you receive your package."
    )
    
    try:
        sms.send(buyer_message, [buyer_phone])
        print(f"Success: OTP sent to {buyer_phone}")
    except Exception as e:
        print(f"Error sending buyer SMS: {e}")

    # Hardcoded for the hackathon demo
    available_riders = ["+254711111111", "+254722222222"] 
    rider_message = (
        f"MzigoSafe Job Alert! New delivery. Earn Ksh {delivery_fee}. "
        f"Dial *384*XXX# to accept Delivery #{delivery_id}."
    )
    
    try:
        sms.send(rider_message, available_riders)
        print(f"Success: Broadcast sent to riders")
    except Exception as e:
        print(f"Error broadcasting to riders: {e}")