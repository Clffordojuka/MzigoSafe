from fastapi import APIRouter, Form, Response, Depends
from sqlalchemy.orm import Session
from database import get_db
from routers.sms import dispatch_logistics_alerts
import models
import random

def generate_otp():
    return str(random.randint(1000, 9999))

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
        user = models.User(phone_number=user_phone, role=models.UserRole.seller)
        db.add(user)
        db.commit()
        db.refresh(user)

    # =========================================================================
    # 1. DYNAMIC RIDER FLOW (Isolated Rider App)
    # =========================================================================
    if user.role == models.UserRole.rider:
        active_delivery = db.query(models.Delivery).filter(
            models.Delivery.rider_id == user.user_id,
            models.Delivery.status.in_([models.DeliveryStatus.rider_assigned, models.DeliveryStatus.in_transit])
        ).first()

        if active_delivery:
            # STATE A: Waiting for Pickup
            if active_delivery.status == models.DeliveryStatus.rider_assigned:
                if len(inputs) == 0:
                    seller = db.query(models.User).filter(models.User.user_id == active_delivery.seller_id).first()
                    response = (
                        f"CON Pickup Job Active!\n"
                        f"Seller: {seller.phone_number}\n"
                        f"Enter 4-digit Pickup OTP:"
                    )
                    return Response(content=response, media_type="text/plain")
                elif len(inputs) == 1:
                    if inputs[0] == active_delivery.pickup_otp:
                        active_delivery.status = models.DeliveryStatus.in_transit
                        db.commit()
                        response = "END OTP Verified! Package IN TRANSIT. Dial back when you reach the buyer."
                    else:
                        response = "END Invalid Pickup OTP. Try again."
                    return Response(content=response, media_type="text/plain")
            
            # STATE B: Waiting for Dropoff
            elif active_delivery.status == models.DeliveryStatus.in_transit:
                if len(inputs) == 0:
                    buyer = db.query(models.User).filter(models.User.user_id == active_delivery.buyer_id).first()
                    response = (
                        f"CON Dropoff Job Active!\n"
                        f"Buyer: {buyer.phone_number}\n"
                        f"Enter 4-digit Delivery OTP:"
                    )
                    return Response(content=response, media_type="text/plain")
                elif len(inputs) == 1:
                    if inputs[0] == active_delivery.dropoff_otp:
                        active_delivery.status = models.DeliveryStatus.delivered
                        
                        seller = db.query(models.User).filter(models.User.user_id == active_delivery.seller_id).first()
                        rider = user 
                        
                        seller.wallet_balance += active_delivery.item_price
                        rider.wallet_balance += active_delivery.delivery_fee
                        
                        db.commit()
                        response = f"END Delivery Complete! KES {active_delivery.delivery_fee} added to your wallet."
                    else:
                        response = "END Invalid Delivery OTP. Try again."
                    return Response(content=response, media_type="text/plain")
        
        # STATE C: Idle Rider - Looking for work
        else:
            if len(inputs) == 0:
                response = "CON MzigoSafe Rider App\n1. Find Available Jobs\n2. Wallet Balance"
                return Response(content=response, media_type="text/plain")
            
            elif inputs[0] == "1":
                available_job = db.query(models.Delivery).filter(
                    models.Delivery.status == models.DeliveryStatus.funds_secured,
                    models.Delivery.rider_id == None
                ).order_by(models.Delivery.created_at.desc()).first()
                
                if not available_job:
                    response = "END No pending deliveries available right now."
                    return Response(content=response, media_type="text/plain")
                
                if len(inputs) == 1:
                    seller = db.query(models.User).filter(models.User.user_id == available_job.seller_id).first()
                    response = (
                        f"CON New Job Available!\n"
                        f"Pickup: {seller.phone_number}\n"
                        f"Fee: Ksh {available_job.delivery_fee}\n"
                        f"1. Accept Job\n2. Ignore"
                    )
                    return Response(content=response, media_type="text/plain")
                elif len(inputs) == 2:
                    if inputs[1] == "1":
                        available_job.rider_id = user.user_id
                        available_job.status = models.DeliveryStatus.rider_assigned
                        db.commit()
                        response = "END Job Accepted! Dial back to enter the Pickup OTP when you arrive."
                    else:
                        response = "END Job ignored."
                    return Response(content=response, media_type="text/plain")
            
            elif inputs[0] == "2":
                response = f"END Your virtual wallet balance is: KES {user.wallet_balance}"
                return Response(content=response, media_type="text/plain")
            else:
                response = "END Invalid choice."
                return Response(content=response, media_type="text/plain")

    # =========================================================================
    # 2. DYNAMIC BUYER FLOW (The Virtual Escrow Trap)
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
                    user.wallet_balance -= total
                    pending_delivery.status = models.DeliveryStatus.funds_secured
                    
                    pickup_otp = generate_otp()
                    dropoff_otp = generate_otp()
                    pending_delivery.pickup_otp = pickup_otp
                    pending_delivery.dropoff_otp = dropoff_otp
                    
                    db.commit()
                    
                    # 2. TRIGGER THE SMS ALERTS HERE!
                    seller = db.query(models.User).filter(models.User.user_id == pending_delivery.seller_id).first()
                    dispatch_logistics_alerts(
                        seller_phone=seller.phone_number,
                        buyer_phone=user.phone_number,
                        delivery_fee=float(pending_delivery.delivery_fee),
                        pickup_otp=pickup_otp,
                        dropoff_otp=dropoff_otp
                    )
                    
                    response = "END Payment successful! Funds escrowed. Rider has been dispatched."
                else:
                    response = "END Insufficient wallet balance."
                return Response(content=response, media_type="text/plain")
                
            elif inputs[0] == "2":
                pending_delivery.status = models.DeliveryStatus.cancelled
                db.commit()
                response = "END Delivery request declined successfully."
                return Response(content=response, media_type="text/plain")
                
            else:
                response = "END Invalid choice."
                return Response(content=response, media_type="text/plain")

    # =========================================================================
    # 3. STANDARD SELLER FLOW (Default)
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