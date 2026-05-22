from fastapi import APIRouter, Form, Response, Depends
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter()

@router.post("/")
async def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    db: Session = Depends(get_db)
):
    inputs = text.split("*") if text else []
    
    if len(inputs) == 0:
        response = "CON Welcome to MzigoSafe\n1. Send Package\n2. Track Delivery\n3. Wallet Balance"

    elif inputs[0] == "1":
        if len(inputs) == 1:
            response = "CON Enter Buyer Phone Number (e.g., 07XXXXXXXX):"
            
        elif len(inputs) == 2:
            response = "CON Enter the Price of the Item (Ksh):"
            
        elif len(inputs) == 3:
            response = "CON Enter the Delivery Fee (Ksh):"
            
        elif len(inputs) == 4:
            buyer_phone, item_price, delivery_fee = inputs[1], int(inputs[2]), int(inputs[3])
            total = item_price + delivery_fee
            
            response = (
                f"CON Send package to {buyer_phone}?\n"
                f"Item: Ksh {item_price}\n"
                f"Delivery: Ksh {delivery_fee}\n"
                f"Total: Ksh {total}\n"
                f"1. Confirm\n2. Cancel"
            )
            
        elif len(inputs) == 5:
            if inputs[4] == "1":
                # Hackathon Stub: Save to DB here
                response = "END Request sent! The buyer has been notified to secure funds."
            else:
                response = "END Delivery request cancelled."

    else:
        response = "END Invalid choice or feature coming soon."

    return Response(content=response, media_type="text/plain")