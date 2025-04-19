from celery import Celery
from backend.config import settings
from backend.auth.email_utils import send_verification_email

celery = Celery(
    __name__,
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND_URL,
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
)

celery.autodiscover_tasks(["backend.tasks"])