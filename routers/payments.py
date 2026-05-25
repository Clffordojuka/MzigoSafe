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
        
        # 1. Fetch the delivery from the database
        delivery = db.query(models.Delivery).filter(models.Delivery.delivery_id == int(delivery_id)).first()
        
        if delivery:
            # 2. Update status and save OTP
            delivery.status = models.DeliveryStatus.funds_secured
            otp = generate_otp()
            delivery.otp_code = otp
            db.commit()
            
            # 3. Fetch buyer to get their actual phone number
            buyer = db.query(models.User).filter(models.User.user_id == delivery.buyer_id).first()
            
            # 4. Dispatch the SMS alerts
            dispatch_escrow_success_alerts(
                buyer_phone=buyer.phone_number,
                delivery_id=delivery.delivery_id,
                delivery_fee=float(delivery.delivery_fee),
                otp=otp
            )
    else:
        print(f"Escrow Failed for Delivery ID {delivery_id}. Reason: {data.get('description')}")
        # Mark as cancelled if payment fails
        delivery = db.query(models.Delivery).filter(models.Delivery.delivery_id == int(delivery_id)).first()
        if delivery:
            delivery.status = models.DeliveryStatus.cancelled
            db.commit()
        
    return {"status": "received"}