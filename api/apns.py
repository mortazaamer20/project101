# apns_helper.py

import asyncio
from kalyke import ApnsClient, Payload, PayloadAlert
from django.conf import settings
from .models import DeviceToken
import logging

logger = logging.getLogger(__name__)

# Initialize APNs Client with required configurations
apns_client  = ApnsClient(
    use_sandbox=True,
    team_id="YOUR_TEAM_ID",
    auth_key_id="AUTH_KEY_ID",
    auth_key_filepath="/path/to/AuthKey_AUTH_KEY_ID.p8",
)

def create_payload(title, message):
    """
    Creates a PayloadAlert and Payload for APNs.
    """
    alert = PayloadAlert(title=title, body=message)
    payload = Payload(alert=alert, sound="default", badge=1)
    return payload

async def send_ios_push_notification(token, title, message):
    """
    Sends a single push notification to a specified device token.
    """
    payload = create_payload(title, message)
    try:
        response = await apns_client.send_push(token=token, payload=payload)
        if response.status_code == 200:
            logger.info(f"Notification sent to {token}: {title} - {message}")
            return True
        else:
            logger.error(f"Failed to send notification to {token}: {response.status_code} - {response.reason}")
            return False
    except Exception as e:
        logger.error(f"Exception sending notification to {token}: {e}")
        return False

def send_notification_to_all_devices(title, message):
    """
    Sends a push notification to all registered device tokens.
    Manages the event loop to avoid RuntimeError.
    """
    tokens = DeviceToken.objects.values_list('token', flat=True)
    try:
        asyncio.run(asyncio.gather(
            *[send_ios_push_notification(token, title, message) for token in tokens]
        ))
    except RuntimeError as e:
        logger.error(f"RuntimeError while sending notifications: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending notifications: {e}")
