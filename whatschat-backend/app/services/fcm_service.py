import logging
import os
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_initialized = False

def _init():
    global _initialized
    if not _initialized:
        try:
            cred_path = os.path.join(os.path.dirname(__file__), '../../firebase-adminsdk.json')
            cred = credentials.Certificate(os.path.abspath(cred_path))
            firebase_admin.initialize_app(cred)
            _initialized = True
        except Exception as e:
            logger.error(f"Firebase init failed: {e}")

def send_push_notification(fcm_token: str, title: str, body: str, data: dict = None):
    try:
        _init()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            android=messaging.AndroidConfig(priority='high'),
            token=fcm_token,
        )
        messaging.send(message)
        logger.info(f"FCM sent to {fcm_token[:20]}...")
    except Exception as e:
        logger.warning(f"FCM send failed: {e}")
