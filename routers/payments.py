import os
import requests
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.sms import dispatch_escrow_success_alerts, generate_otp

router = APIRouter()

def initiate_mpesa_escrow_push(buyer_phone: str, total_amount: float, delivery_id: int):
    url = "https://payments.sandbox.africastalking.com/mobile/checkout/request"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "apiKey": os.getenv("AT_API_KEY")
    }
    payload = {
        "username": os.getenv("AT_USERNAME"),
        "productName": "MzigoSafe", 
        "phoneNumber": buyer_phone,
        "currencyCode": "KES",
        "amount": total_amount,
        "metadata": {"delivery_id": str(delivery_id)}
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        print("Payment initiation failed:", str(e))
        return False

@router.post("/callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    status = data.get("status")
    metadata = data.get("metadata", {})
    delivery_id = metadata.get("delivery_id")
    
    if status == "Success":
        print(f"Escrow Secured for Delivery ID {delivery_id}")
        
        # In a real build, we'd update the DB status here.
        # Generate OTP and alert everyone
        otp = generate_otp()
        dispatch_escrow_success_alerts(
            buyer_phone="+254700000000", # Fetch from DB in production
            delivery_id=delivery_id,
            delivery_fee=200,            # Fetch from DB in production
            otp=otp
        )
    else:
        print(f"Escrow Failed for Delivery ID {delivery_id}. Reason: {data.get('description')}")
        
    return {"status": "received"}