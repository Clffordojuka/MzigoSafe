import requests
import random
import string

# 1. PASTE YOUR CHECKOUT ID HERE
CHECKOUT_ID = "ws_CO_03062026230657776722222222" 

# Generate a random receipt number so the database doesn't block it!
random_receipt = "SIM" + "".join(random.choices(string.ascii_uppercase + string.digits, k=7))

# 2. Safaricom JSON payload
safaricom_mock_payload = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "12345-67890-1",
            "CheckoutRequestID": CHECKOUT_ID,
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 5000.00},
                    {"Name": "MpesaReceiptNumber", "Value": random_receipt},
                    {"Name": "PhoneNumber", "Value": 254722222222}
                ]
            }
        }
    }
}

# 3. Fire it at your local webhook endpoint
print(f"Simulating Daraja Callback for {CHECKOUT_ID}...")
print(f"Using Receipt Number: {random_receipt}")
try:
    response = requests.post("http://localhost:8000/api/mpesa/callback", json=safaricom_mock_payload)
    print(f"Server Response: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")