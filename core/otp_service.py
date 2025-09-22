import os
import random
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# Load Twilio credentials
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")  # Your Twilio phone number

# In-memory OTP store (for demo, should use Redis in production)
otp_store = {}

def send_otp(phone: str) -> int:
    """Generate OTP and send via SMS using Twilio."""
    if not TWILIO_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE:
        raise ValueError("Twilio credentials not set in .env")

    otp = random.randint(100000, 999999)
    otp_store[phone] = otp  # store OTP temporarily

    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f"Your Insurance Claim OTP is {otp}",
        from_=TWILIO_PHONE,
        to=phone
    )
    # print(f"[DEBUG] OTP {otp} sent to {phone}, SID={message.sid}")
    return otp

def verify_otp(user_input: str, phone: str) -> bool:
    """Verify OTP entered by user against stored OTP."""
    try:
        expected = otp_store.get(phone)
        return expected is not None and str(expected) == str(user_input)
    finally:
        # Always delete OTP after check (one-time use)
        if phone in otp_store:
            del otp_store[phone]
