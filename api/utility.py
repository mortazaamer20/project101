import random
from django.core.cache import cache
from django.conf import settings
from twilio.rest import Client

def send_whatsapp_otp(phone_number):
    # Generate a random 6-digit OTP code
    otp = random.randint(100000, 999999)
    
    # Store the OTP in cache for 5 minutes (300 seconds)
    cache.set(f"otp:{phone_number}", otp, timeout=600)
    
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)

    # Replace this with your own verified WhatsApp template content SID
    # This template should have a single variable {{1}} for the OTP
    content_sid='HX229f5a04fd0510ce1b071852155d3e75',
    content_variables = f'{{"1":"{otp}"}}'

    # Ensure phone_number is in E.164 format and prepend "whatsapp:"
    if not phone_number.startswith('whatsapp:'):
        phone_number = 'whatsapp:' + phone_number

    message = client.messages.create(
      from_='whatsapp:+14155238886',  # Your Twilio WhatsApp-enabled number
      content_sid=content_sid,
      content_variables=content_variables,
      to=phone_number
    )
    return otp
