from fastapi import APIRouter, Form, Response, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.sms import dispatch_escrow_success_alerts, generate_otp

router = APIRouter()

@router.post("/")
async def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    db: Session = Depends(get_db)
):
    user_phone = phoneNumber if phoneNumber.startswith("+") else f"+{phoneNumber.strip()}"
    inputs = text.split("*") if text else []
    
    user = db.query(models.User).filter(models.User.phone_number == user_phone).first()
    if not user:
        # Organic creation: If we don't know them, they default to a seller/buyer hybrid
        user = models.User(phone_number=user_phone, role=models.UserRole.seller)
        db.add(user)
        db.commit()
        db.refresh(user)

    # =========================================================================
    # DYNAMIC BUYER FLOW (The Virtual Escrow Trap)
    # =========================================================================
    pending_delivery = db.query(models.Delivery).filter(
        models.Delivery.buyer_id == user.user_id,
        models.Delivery.status == models.DeliveryStatus.pending_buyer_payment
    ).order_by(models.Delivery.created_at.desc()).first()

    if pending_delivery:
        total = pending_delivery.item_price + pending_delivery.delivery_fee
        
        if len(inputs) == 0:
            response = (
                f"CON MzigoSafe Escrow Request!\n"
                f"Total Due: Ksh {total}\n"
                f"Your Wallet: Ksh {user.wallet_balance}\n"
                f"1. Pay from Wallet\n"
                f"2. Decline Order"
            )
            return Response(content=response, media_type="text/plain")
            
        elif len(inputs) == 1:
            if inputs[0] == "1":
                if user.wallet_balance >= total:
                    # 1. Deduct funds (Virtual Escrow)
                    user.wallet_balance -= total
                    pending_delivery.status = models.DeliveryStatus.funds_secured
                    
                    # 2. Generate Dual OTPs
                    pickup_otp = generate_otp()
                    dropoff_otp = generate_otp()
                    pending_delivery.pickup_otp = pickup_otp
                    pending_delivery.dropoff_otp = dropoff_otp
                    
                    db.commit()
                    
                    # 3. Alert everyone via SMS
                    # (We will implement the detailed SMS logic next)
                    # dispatch_escrow_success_alerts(...)
                    
                    response = "END Payment successful! Funds escrowed. Rider has been dispatched."
                else:
                    response = "END Insufficient wallet balance. Please top up and try again."
                return Response(content=response, media_type="text/plain")
                
            elif inputs[0] == "2":
                pending_delivery.status = models.DeliveryStatus.cancelled
                db.commit()
                response = "END Delivery request declined successfully."
                return Response(content=response, media_type="text/plain")
                
            else:
                response = "END Invalid choice. Please dial again."
                return Response(content=response, media_type="text/plain")

    # =========================================================================
    # STANDARD SELLER FLOW
    # =========================================================================
    if len(inputs) == 0:
        response = "CON Welcome to MzigoSafe\n1. Send Package\n2. Track Delivery\n3. Wallet Balance"

    elif inputs[0] == "1":
        if len(inputs) == 1:
            response = "CON Enter Buyer Phone Number (e.g., +2547XXXXXXXX):"
            
        elif len(inputs) == 2:
            response = "CON Enter the Price of the Item (Ksh):"
            
        elif len(inputs) == 3:
            response = "CON Enter the Delivery Fee (Ksh):"
            
        elif len(inputs) == 4:
            buyer_phone = inputs[1]
            try:
                item_price = int(inputs[2])
                delivery_fee = int(inputs[3])
                total = item_price + delivery_fee
                
                response = (
                    f"CON Send package to {buyer_phone}?\n"
                    f"Item: Ksh {item_price}\n"
                    f"Delivery: Ksh {delivery_fee}\n"
                    f"Total: Ksh {total}\n"
                    f"1. Confirm\n2. Cancel"
                )
            except ValueError:
                response = "END Invalid inputs. Please use integers."
            
        elif len(inputs) == 5:
            if inputs[4] == "1":
                raw_buyer_phone = inputs[1]
                if not raw_buyer_phone.startswith("+"):
                    if raw_buyer_phone.startswith("0"):
                        raw_buyer_phone = "+254" + raw_buyer_phone[1:]
                    else:
                        raw_buyer_phone = "+" + raw_buyer_phone

                item_price = int(inputs[2])
                delivery_fee = int(inputs[3])
                
                buyer_user = db.query(models.User).filter(models.User.phone_number == raw_buyer_phone).first()
                if not buyer_user:
                    # Organic creation of the buyer
                    buyer_user = models.User(phone_number=raw_buyer_phone, role=models.UserRole.buyer)
                    db.add(buyer_user)
                    db.commit()
                    db.refresh(buyer_user)

                new_delivery = models.Delivery(
                    seller_id=user.user_id,
                    buyer_id=buyer_user.user_id,
                    item_price=item_price,
                    delivery_fee=delivery_fee,
                    status=models.DeliveryStatus.pending_buyer_payment
                )
                db.add(new_delivery)
                db.commit()
                
                response = f"END Request sent! Order #{new_delivery.delivery_id} pending buyer verification."
            else:
                response = "END Delivery request cancelled."

    elif inputs[0] == "2":
        response = "END Tracking module coming soon."
    elif inputs[0] == "3":
        response = f"END Your virtual wallet balance is: KES {user.wallet_balance}"
    else:
        response = "END Invalid choice."

    return Response(content=response, media_type="text/plain")