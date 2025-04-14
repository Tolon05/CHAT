from celery import Celery
from config import settings

celery = Celery(
    __name__,
    broker=settings.CELERY_BROKER_URL,
    backend="redis://localhost:6379/0"
)

@celery.task
async def send_verification_email_task(to_email: str, code: str):
    from backend.email_utils import send_verification_email
    await send_verification_email(to_email, code)
