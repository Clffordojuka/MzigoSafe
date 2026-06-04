import os
import requests
from requests.auth import HTTPBasicAuth
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Daraja Sandbox Endpoints
MPESA_AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
MPESA_STK_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
MPESA_B2C_URL = "https://sandbox.safaricom.co.ke/mpesa/b2c/v3/paymentrequest"

def get_access_token():
    """Fetches the OAuth token from Safaricom Daraja."""
    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    
    try:
        res = requests.get(MPESA_AUTH_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        res.raise_for_status()
        return res.json()['access_token']
    except Exception as e:
        print(f"Failed to get M-Pesa token: {e}")
        return None

def format_phone_number(phone: str):
    """Safaricom requires the phone number in the format 2547XXXXXXXX."""
    phone = phone.strip().replace("+", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    return phone

def initiate_stk_push(phone_number: str, amount: int, reference: str, description: str):
    """Triggers the M-Pesa PIN prompt on the user's phone."""
    access_token = get_access_token()
    if not access_token:
        return {"error": "Authentication failed"}

    # Fetch configurations from .env
    shortcode = os.getenv("MPESA_SHORTCODE", "174379")
    passkey = os.getenv("MPESA_PASSKEY")
    callback_url = os.getenv("MPESA_CALLBACK_URL") 

    # Generate the base64 encoded password
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    data_to_encode = shortcode + passkey + timestamp
    password = base64.b64encode(data_to_encode.encode('utf-8')).decode('utf-8')

    formatted_phone = format_phone_number(phone_number)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Construct the payload
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": formatted_phone,
        "PartyB": shortcode,
        "PhoneNumber": formatted_phone,
        "CallBackURL": callback_url,
        "AccountReference": str(reference),
        "TransactionDesc": description
    }

    try:
        response = requests.post(MPESA_STK_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print(f"STK Push Initiated: {result.get('CheckoutRequestID')}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"STK Push Failed: {e}")
        if response is not None:
            print(response.text)
        return {"error": str(e)}

def trigger_b2c_payout(phone_number: str, amount: int, command_id: str, remarks: str, occassion: str = ""):
    """
    Sends money FROM your paybill TO a customer's M-Pesa account.
    command_id can be: 'BusinessPayment', 'SalaryPayment', or 'PromotionPayment'
    """
    access_token = get_access_token()
    if not access_token:
        return {"error": "Authentication failed"}

    # Fetch B2C configurations from .env
    shortcode = os.getenv("MPESA_B2C_SHORTCODE", os.getenv("MPESA_SHORTCODE")) 
    initiator_name = os.getenv("MPESA_B2C_INITIATOR_NAME", "testapi")
    security_credential = os.getenv("MPESA_B2C_SECURITY_CREDENTIAL", "SANDBOX_CREDENTIAL_HERE")
    callback_url = os.getenv("MPESA_CALLBACK_URL").replace("callback", "b2c-callback") # E.g., /api/mpesa/b2c-callback
    
    formatted_phone = format_phone_number(phone_number)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "InitiatorName": initiator_name,
        "SecurityCredential": security_credential,
        "CommandID": command_id,
        "Amount": int(amount),
        "PartyA": shortcode,
        "PartyB": formatted_phone,
        "Remarks": remarks,
        "QueueTimeOutURL": callback_url,
        "ResultURL": callback_url,
        "Occassion": occassion
    }

    try:
        response = requests.post(MPESA_B2C_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print(f"B2C Payout Initiated for {formatted_phone}: {result.get('ConversationID')}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"B2C Payout Failed for {formatted_phone}: {e}")
        if response is not None:
            print(response.text)
        return {"error": str(e)}