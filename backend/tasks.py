from backend.celery_worker import celery
from backend.auth.email_utils import send_verification_email

@celery.task
async def send_verification_email_task(to_email: str, code: str):
    await send_verification_email(to_email, code)
