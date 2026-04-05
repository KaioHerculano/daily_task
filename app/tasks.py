import logging

from celery import shared_task
from django.core.mail import EmailMultiAlternatives

from utils.security import mask_email

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_email_task(self, subject, body, from_email, to_email, html_email=None):
    masked_to_email = mask_email(to_email)

    try:
        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])

        if html_email:
            email_message.attach_alternative(html_email, "text/html")

        email_message.send()

        logger.info(f"[EMAIL] Sucesso ao enviar para {masked_to_email}")

    except Exception as e:
        logger.error(f"[EMAIL] Erro ao enviar para {masked_to_email}: {str(e)}")
        raise
