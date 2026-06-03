from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
from routers.sms import dispatch_logistics_alerts
import models
import random

router = APIRouter()

def generate_otp():
    return str(random.randint(1000, 9999))

@router.post("/callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    """
    Safaricom Daraja will hit this URL asynchronously after the user 
    completes or cancels the M-Pesa PIN prompt on their phone.
    """
    try:
        # 1. Parse the Safaricom JSON payload
        payload = await request.json()
        callback_data = payload.get("Body", {}).get("stkCallback", {})
        
        result_code = callback_data.get("ResultCode")
        checkout_id = callback_data.get("CheckoutRequestID")
        
        # 2. Look up the pending transaction in our Virtual Ledger
        ledger_entry = db.query(models.EscrowLedger).filter(
            models.EscrowLedger.mpesa_checkout_id == checkout_id
        ).first()
        
        # If we can't find it, Safaricom might be sending a duplicate or old ping. 
        # Always return Success to Safaricom so they stop retrying.
        if not ledger_entry:
            return {"ResultCode": 0, "ResultDesc": "Accepted"}
            
        # 3. Find the associated Delivery order
        delivery = db.query(models.Delivery).filter(
            models.Delivery.delivery_id == ledger_entry.delivery_id
        ).first()
        
        # 4. Handle the Payment Result
        if result_code == 0:
            # ✅ PAYMENT SUCCESSFUL
            
            # Extract the actual M-Pesa Receipt Number for accounting
            meta_items = callback_data.get("CallbackMetadata", {}).get("Item", [])
            receipt_no = next((item["Value"] for item in meta_items if item["Name"] == "MpesaReceiptNumber"), "UNKNOWN")
            
            # Update the Escrow Ledger
            ledger_entry.status = models.PaymentStatus.escrowed
            ledger_entry.mpesa_checkout_id = str(receipt_no)
            
            # Secure the delivery and generate the Dual-OTPs
            delivery.status = models.DeliveryStatus.funds_secured
            pickup_otp = generate_otp()
            dropoff_otp = generate_otp()
            delivery.pickup_otp = pickup_otp
            delivery.dropoff_otp = dropoff_otp
            
            db.commit()
            
            # Blast the SMS alerts!
            seller = db.query(models.User).filter(models.User.user_id == delivery.seller_id).first()
            buyer = db.query(models.User).filter(models.User.user_id == delivery.buyer_id).first()
            
            dispatch_logistics_alerts(
                seller_phone=seller.phone_number,
                buyer_phone=buyer.phone_number,
                delivery_fee=float(delivery.delivery_fee),
                pickup_otp=pickup_otp,
                dropoff_otp=dropoff_otp
            )
            print(f"💰 M-Pesa Success! Receipt {receipt_no} secured. SMS fired.")

        else:
            # ❌ PAYMENT FAILED / CANCELLED (e.g., Wrong PIN, Insufficient Funds)
            result_desc = callback_data.get("ResultDesc", "Failed")
            print(f"⚠️ M-Pesa Failed: {result_desc}")
            
            # Revert the ledger and cancel the delivery order
            ledger_entry.status = models.PaymentStatus.failed
            delivery.status = models.DeliveryStatus.cancelled
            db.commit()

        # Daraja REQUIRES this exact JSON response, otherwise it will spam your server for 24 hours.
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
        
    except Exception as e:
        print(f"🚨 Error in M-Pesa Webhook: {e}")
        return {"ResultCode": 0, "ResultDesc": "Accepted"}