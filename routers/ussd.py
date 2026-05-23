from fastapi import APIRouter, Form, Response, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.payments import initiate_mpesa_escrow_push

router = APIRouter()

@router.post("/")
async def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    db: Session = Depends(get_db)
):
    # Standardize incoming phone number format
    user_phone = phoneNumber if phoneNumber.startswith("+") else f"+{phoneNumber.strip()}"
    inputs = text.split("*") if text else []
    
    # 1. Identify or auto-register the calling user in our DB
    user = db.query(models.User).filter(models.User.phone_number == user_phone).first()
    if not user:
        # Default auto-registration for demo fallback
        user = models.User(phone_number=user_phone, role=models.UserRole.buyer)
        db.add(user)
        db.commit()
        db.refresh(user)

    response = ""

    # =========================================================================
    # DYNAMIC BUYER FLOW (Intercept menu if an active escrow request exists)
    # =========================================================================
    pending_delivery = db.query(models.Delivery).filter(
        models.Delivery.buyer_id == user.user_id,
        models.Delivery.status == models.DeliveryStatus.pending_buyer_payment
    ).order_by(models.Delivery.created_at.desc()).first()

    # If the buyer dials in and hasn't started navigating the seller menu explicitly
    if pending_delivery and (len(inputs) == 0 or inputs[0] not in ["1", "2", "3"]):
        if len(inputs) == 0:
            total = pending_delivery.item_price + pending_delivery.delivery_fee
            response = (
                f"CON MzigoSafe Escrow Request!\n"
                f"Total Due: Ksh {total}\n"
                f"1. Approve & Pay Now\n"
                f"2. Decline Order"
            )
        elif inputs[0] == "1":
            total = pending_delivery.item_price + pending_delivery.delivery_fee
            # Trigger our direct REST API wrapper for M-Pesa push
            push_triggered = initiate_mpesa_escrow_push(
                buyer_phone=user_phone,
                total_amount=float(total),
                delivery_id=pending_delivery.delivery_id
            )
            if push_triggered:
                response = "END STK PIN Prompt sent to your phone. Complete payment to secure escrow."
            else:
                response = "END Failed to trigger payment. Please try again later."
        elif inputs[0] == "2":
            pending_delivery.status = models.DeliveryStatus.cancelled
            db.commit()
            response = "END Delivery request declined successfully."
        
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
                response = "END Invalid inputs. Please use integers for currency values."
            
        elif len(inputs) == 5:
            if inputs[4] == "1":
                raw_buyer_phone = inputs[1]
                
                # Format local phone syntax to standard E.164 (+254...)
                if not raw_buyer_phone.startswith("+"):
                    if raw_buyer_phone.startswith("0"):
                        raw_buyer_phone = "+254" + raw_buyer_phone[1:]
                    else:
                        raw_buyer_phone = "+" + raw_buyer_phone

                item_price = int(inputs[2])
                delivery_fee = int(inputs[3])
                
                # Fetch or create the buyer profile record
                buyer_user = db.query(models.User).filter(models.User.phone_number == raw_buyer_phone).first()
                if not buyer_user:
                    buyer_user = models.User(phone_number=raw_buyer_phone, role=models.UserRole.buyer)
                    db.add(buyer_user)
                    db.commit()
                    db.refresh(buyer_user)

                # Persist the active delivery to PostgreSQL
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
        response = "END Active shipment pipeline interfaces coming soon."
    elif inputs[0] == "3":
        response = "END Current verified wallet balance: KES 0.00."
    else:
        response = "END Invalid choice or feature coming soon."

    return Response(content=response, media_type="text/plain")