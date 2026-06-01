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
    
    # Stateful routing relies only on the MOST RECENT input from the user
    raw_inputs = text.split("*") if text else []
    latest_input = raw_inputs[-1] if raw_inputs else ""
    
    # =========================================================================
    # 1. USER IDENTIFICATION & AUTO-REGISTRATION
    # =========================================================================
    user = db.query(models.User).filter(models.User.phone_number == user_phone).first()
    if not user:
        # Auto-detect the test rider based on their number
        if "733333333" in user_phone:
            user = models.User(phone_number=user_phone, role=models.UserRole.rider)
        else:
            user = models.User(phone_number=user_phone, role=models.UserRole.seller)
            
        db.add(user)
        db.commit()
        db.refresh(user)

    # =========================================================================
    # 2. SESSION STATE MANAGEMENT
    # =========================================================================
    ussd_session = db.query(models.UssdSession).filter(models.UssdSession.session_id == sessionId).first()
    
    # If text is empty, it's a fresh dial-in. Reset state to MAIN_MENU.
    if text == "":
        if ussd_session:
            ussd_session.current_screen = "MAIN_MENU"
            ussd_session.meta_data = {}
        else:
            ussd_session = models.UssdSession(
                session_id=sessionId,
                phone_number=user_phone,
                current_screen="MAIN_MENU",
                meta_data={}
            )
            db.add(ussd_session)
        db.commit()
    
    # Safely load the JSON dictionary holding their previous answers
    session_data = ussd_session.meta_data.copy() if ussd_session.meta_data else {}

    # =========================================================================
    # 3. DYNAMIC RIDER FLOW (With Dispute Resolution)
    # =========================================================================
    if user.role == models.UserRole.rider:
        active_delivery = db.query(models.Delivery).filter(
            models.Delivery.rider_id == user.user_id,
            models.Delivery.status.in_([models.DeliveryStatus.rider_assigned, models.DeliveryStatus.in_transit])
        ).first()

        if active_delivery:
            # STATE A: Waiting for Pickup
            if active_delivery.status == models.DeliveryStatus.rider_assigned:
                if text == "" or ussd_session.current_screen == "MAIN_MENU":
                    ussd_session.current_screen = "RIDER_PICKUP_MENU"
                    db.commit()
                    seller = db.query(models.User).filter(models.User.user_id == active_delivery.seller_id).first()
                    return Response(f"CON Pickup Job Active!\nSeller: {seller.phone_number}\n1. Enter Pickup OTP\n2. Cancel/Reject Job", media_type="text/plain")
                
                elif ussd_session.current_screen == "RIDER_PICKUP_MENU":
                    if latest_input == "1":
                        ussd_session.current_screen = "ENTERING_PICKUP_OTP"
                        db.commit()
                        return Response("CON Enter 4-digit Pickup OTP:", media_type="text/plain")
                    elif latest_input == "2":
                        # Rider rejects the job before picking up: release the job back to the board
                        active_delivery.rider_id = None
                        active_delivery.status = models.DeliveryStatus.funds_secured
                        ussd_session.current_screen = "MAIN_MENU"
                        db.commit()
                        return Response("END Job cancelled. It has been returned to the available job board.", media_type="text/plain")
                
                elif ussd_session.current_screen == "ENTERING_PICKUP_OTP":
                    if latest_input == active_delivery.pickup_otp:
                        active_delivery.status = models.DeliveryStatus.in_transit
                        ussd_session.current_screen = "MAIN_MENU"
                        db.commit()
                        return Response("END OTP Verified! Package IN TRANSIT. Dial back when you reach the buyer.", media_type="text/plain")
                    return Response("CON Invalid OTP. Try again\nEnter 4-digit Pickup OTP:", media_type="text/plain")
            
            # STATE B: Waiting for Dropoff
            elif active_delivery.status == models.DeliveryStatus.in_transit:
                if text == "" or ussd_session.current_screen == "MAIN_MENU":
                    ussd_session.current_screen = "RIDER_DROPOFF_MENU"
                    db.commit()
                    buyer = db.query(models.User).filter(models.User.user_id == active_delivery.buyer_id).first()
                    return Response(f"CON Dropoff Job Active!\nBuyer: {buyer.phone_number}\n1. Enter Delivery OTP\n2. Buyer Rejected / Issue", media_type="text/plain")
                
                elif ussd_session.current_screen == "RIDER_DROPOFF_MENU":
                    if latest_input == "1":
                        ussd_session.current_screen = "ENTERING_DROPOFF_OTP"
                        db.commit()
                        return Response("CON Enter 4-digit Delivery OTP:", media_type="text/plain")
                    elif latest_input == "2":
                        # DISPUTE TRIGGERED: Execute reverse logistics refund
                        buyer = db.query(models.User).filter(models.User.user_id == active_delivery.buyer_id).first()
                        
                        # Refund item price to buyer, rider still takes delivery fee
                        buyer.wallet_balance += active_delivery.item_price
                        user.wallet_balance += active_delivery.delivery_fee
                        
                        active_delivery.status = models.DeliveryStatus.cancelled
                        ussd_session.current_screen = "MAIN_MENU"
                        db.commit()
                        
                        return Response(f"END Dispute Logged. Item price refunded to Buyer. KES {active_delivery.delivery_fee} credited to your wallet for the trip.", media_type="text/plain")
                
                elif ussd_session.current_screen == "ENTERING_DROPOFF_OTP":
                    if latest_input == active_delivery.dropoff_otp:
                        active_delivery.status = models.DeliveryStatus.delivered
                        seller = db.query(models.User).filter(models.User.user_id == active_delivery.seller_id).first()
                        
                        seller.wallet_balance += active_delivery.item_price
                        user.wallet_balance += active_delivery.delivery_fee
                        
                        ussd_session.current_screen = "MAIN_MENU"
                        db.commit()
                        return Response(f"END Delivery Complete! KES {active_delivery.delivery_fee} added to your wallet.", media_type="text/plain")
                    return Response("CON Invalid OTP. Try again\nEnter 4-digit Delivery OTP:", media_type="text/plain")
        
        # Idle Rider / Job Board
        else:
            if text == "":
                return Response("CON MzigoSafe Rider App\n1. Find Available Jobs\n2. Wallet Balance", media_type="text/plain")
            
            elif latest_input == "1" and ussd_session.current_screen == "MAIN_MENU":
                available_job = db.query(models.Delivery).filter(
                    models.Delivery.status == models.DeliveryStatus.funds_secured,
                    models.Delivery.rider_id == None
                ).order_by(models.Delivery.created_at.desc()).first()
                
                if not available_job:
                    return Response("END No pending deliveries available right now.", media_type="text/plain")
                
                ussd_session.current_screen = "VIEWING_JOB"
                session_data["job_id"] = available_job.delivery_id
                ussd_session.meta_data = session_data
                db.commit()
                
                seller = db.query(models.User).filter(models.User.user_id == available_job.seller_id).first()
                return Response(f"CON New Job Available!\nPickup: {seller.phone_number}\nFee: Ksh {available_job.delivery_fee}\n1. Accept Job\n2. Ignore", media_type="text/plain")
            
            elif ussd_session.current_screen == "VIEWING_JOB":
                if latest_input == "1":
                    job_id = session_data.get("job_id")
                    job = db.query(models.Delivery).filter(models.Delivery.delivery_id == job_id).first()
                    job.rider_id = user.user_id
                    job.status = models.DeliveryStatus.rider_assigned
                    ussd_session.current_screen = "MAIN_MENU"
                    db.commit()
                    return Response("END Job Accepted! Dial back to enter the Pickup OTP when you arrive.", media_type="text/plain")
                
                ussd_session.current_screen = "MAIN_MENU"
                db.commit()
                return Response("END Job ignored.", media_type="text/plain")
            
            elif latest_input == "2":
                return Response(f"END Your virtual wallet balance is: KES {user.wallet_balance}", media_type="text/plain")
            return Response("END Invalid choice.", media_type="text/plain")

    # =========================================================================
    # 4. DYNAMIC BUYER FLOW (The Virtual Escrow Trap)
    # =========================================================================
    pending_delivery = db.query(models.Delivery).filter(
        models.Delivery.buyer_id == user.user_id,
        models.Delivery.status == models.DeliveryStatus.pending_buyer_payment
    ).order_by(models.Delivery.created_at.desc()).first()

    if pending_delivery:
        total = pending_delivery.item_price + pending_delivery.delivery_fee
        
        if text == "":
            return Response(f"CON MzigoSafe Escrow Request!\nTotal Due: Ksh {total}\nYour Wallet: Ksh {user.wallet_balance}\n1. Pay from Wallet\n2. Decline Order", media_type="text/plain")
            
        elif latest_input == "1":
            if user.wallet_balance >= total:
                user.wallet_balance -= total
                pending_delivery.status = models.DeliveryStatus.funds_secured
                
                pickup_otp = generate_otp()
                dropoff_otp = generate_otp()
                pending_delivery.pickup_otp = pickup_otp
                pending_delivery.dropoff_otp = dropoff_otp
                
                db.commit()
                
                seller = db.query(models.User).filter(models.User.user_id == pending_delivery.seller_id).first()
                dispatch_logistics_alerts(
                    seller_phone=seller.phone_number,
                    buyer_phone=user.phone_number,
                    delivery_fee=float(pending_delivery.delivery_fee),
                    pickup_otp=pickup_otp,
                    dropoff_otp=dropoff_otp
                )
                return Response("END Payment successful! Funds escrowed. Rider has been dispatched.", media_type="text/plain")
            return Response("END Insufficient wallet balance.", media_type="text/plain")
            
        elif latest_input == "2":
            pending_delivery.status = models.DeliveryStatus.cancelled
            db.commit()
            return Response("END Delivery request declined successfully.", media_type="text/plain")
            
        return Response("END Invalid choice.", media_type="text/plain")

    # =========================================================================
    # 5. STATEFUL SELLER FLOW (Default)
    # =========================================================================
    if ussd_session.current_screen == "MAIN_MENU":
        if text == "":
            return Response("CON Welcome to MzigoSafe\n1. Send Package\n2. Track Delivery\n3. Wallet Balance", media_type="text/plain")
        
        if latest_input == "1":
            ussd_session.current_screen = "ASK_BUYER_PHONE"
            db.commit()
            return Response("CON Enter Buyer Phone Number (e.g., +2547XXXXXXXX):", media_type="text/plain")
        elif latest_input == "3":
            return Response(f"END Your virtual wallet balance is: KES {user.wallet_balance}", media_type="text/plain")
        else:
            return Response("END Feature coming soon.", media_type="text/plain")

    elif ussd_session.current_screen == "ASK_BUYER_PHONE":
        session_data["buyer_phone"] = latest_input
        ussd_session.meta_data = session_data
        ussd_session.current_screen = "ASK_ITEM_PRICE"
        db.commit()
        return Response("CON Enter the Price of the Item (Ksh):", media_type="text/plain")

    elif ussd_session.current_screen == "ASK_ITEM_PRICE":
        try:
            session_data["item_price"] = int(latest_input)
            ussd_session.meta_data = session_data
            ussd_session.current_screen = "ASK_DELIVERY_FEE"
            db.commit()
            return Response("CON Enter the Delivery Fee (Ksh):", media_type="text/plain")
        except ValueError:
            return Response("CON Invalid input. Please enter a number.\nEnter the Price of the Item (Ksh):", media_type="text/plain")

    elif ussd_session.current_screen == "ASK_DELIVERY_FEE":
        try:
            session_data["delivery_fee"] = int(latest_input)
            ussd_session.meta_data = session_data
            ussd_session.current_screen = "CONFIRM_ORDER"
            db.commit()
            
            total = session_data["item_price"] + session_data["delivery_fee"]
            return Response(f"CON Send package to {session_data['buyer_phone']}?\nItem: Ksh {session_data['item_price']}\nDelivery: Ksh {session_data['delivery_fee']}\nTotal: Ksh {total}\n1. Confirm\n2. Cancel", media_type="text/plain")
        except ValueError:
            return Response("CON Invalid input. Please enter a number.\nEnter the Delivery Fee (Ksh):", media_type="text/plain")

    elif ussd_session.current_screen == "CONFIRM_ORDER":
        if latest_input == "1":
            raw_phone = session_data["buyer_phone"]
            if not raw_phone.startswith("+"):
                raw_phone = "+254" + raw_phone[1:] if raw_phone.startswith("0") else "+" + raw_phone
                
            buyer_user = db.query(models.User).filter(models.User.phone_number == raw_phone).first()
            if not buyer_user:
                buyer_user = models.User(phone_number=raw_phone, role=models.UserRole.buyer)
                db.add(buyer_user)
                db.commit()
                db.refresh(buyer_user)

            new_delivery = models.Delivery(
                seller_id=user.user_id,
                buyer_id=buyer_user.user_id,
                item_price=session_data["item_price"],
                delivery_fee=session_data["delivery_fee"],
                status=models.DeliveryStatus.pending_buyer_payment
            )
            db.add(new_delivery)
            
            ussd_session.current_screen = "MAIN_MENU"
            ussd_session.meta_data = {}
            db.commit()
            
            return Response(f"END Request sent! Order #{new_delivery.delivery_id} pending buyer verification.", media_type="text/plain")
        else:
            ussd_session.current_screen = "MAIN_MENU"
            db.commit()
            return Response("END Delivery request cancelled.", media_type="text/plain")

    return Response("END Invalid session state. Please dial again.", media_type="text/plain")