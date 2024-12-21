import asyncio
import logging
from django.conf import settings
from kalyke import ApnsClient, Payload, PayloadAlert
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from firebase_admin import messaging
from celery import shared_task



logger = logging.getLogger(__name__)

# Initialize APNs Client with required configurations
apns_client = ApnsClient(
    use_sandbox=settings.APNS_USE_SANDBOX,
    team_id=settings.APNS_TEAM_ID,
    auth_key_id=settings.APNS_AUTH_KEY_ID,
    auth_key_filepath=settings.APNS_AUTH_KEY_FILEPATH,
)

def create_payload(title, message):
    """
    Creates a PayloadAlert and Payload for APNs.
    """
    alert = PayloadAlert(title=title, body=message)
    payload = Payload(alert=alert, sound="default", badge=1)
    return payload

@shared_task
def send_ios_push_notification(token, title, message):
    payload = create_payload(title, message)
    try:
        response = apns_client.send_push(token=token, payload=payload)
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        return False

@shared_task
def send_android_push_notification(token, title, message):
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=message),
            token=token,
        )
        messaging.send(message)
        return True
    except Exception:
        return False
    

async def send_notifications_to_tokens(tokens, title, message):
    """
    Sends push notifications to a list of device tokens.
    """
    tasks = [send_ios_push_notification(token, title, message) for token in tokens]
    return await asyncio.gather(*tasks)

def send_notification_to_all_devices(title, message):
    DeviceToken = apps.get_model('api.DeviceToken')
    tokens = DeviceToken.objects.values_list('token', 'platform')

    for token, platform in tokens:
        if platform == 'ios':
            send_ios_push_notification.delay(token, title, message)
        elif platform == 'android':
            send_android_push_notification.delay(token, title, message)


