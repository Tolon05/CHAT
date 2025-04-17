import asyncio
from celery import Celery
from backend.config import settings
from backend.auth.email_utils import send_verification_email

celery = Celery(
    __name__,
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND_URL,
)

@celery.task
def send_verification_email_task(to_email: str, code: str):
    asyncio.run(send_verification_email(to_email, code))
