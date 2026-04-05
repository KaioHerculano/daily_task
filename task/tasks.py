import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from utils.security import mask_email
from .models import TaskDay, DailyReminderLog

logger = logging.getLogger(__name__)


@shared_task
def send_daily_reminders():
    today = timezone.localdate()

    users_studied_today = TaskDay.objects.filter(date=today).values_list('user_id', flat=True)

    users_reminded_today = DailyReminderLog.objects.filter(date=today).values_list('user_id', flat=True)

    target_users = User.objects.filter(is_active=True).exclude(
        id__in=users_studied_today
    ).exclude(
        id__in=users_reminded_today
    )
    
    count = 0
    for user in target_users:
        if not user.email:
            continue

        process_user_reminder.delay(user.id)
        count += 1
        
    logger.info(f"[LEMBRETE] Lembretes processados para {count} usuários na data {today}.")
    return count


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_user_reminder(self, user_id):
    today = timezone.localdate()
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    if DailyReminderLog.objects.filter(user=user, date=today).exists():
        return
        
    context = {'user': user, 'base_url': settings.BASE_URL}
    
    subject = render_to_string('emails/daily_reminder_subject.txt', context).strip()
    body = render_to_string('emails/daily_reminder_body.txt', context)
    html_email = render_to_string('emails/daily_reminder_body.html', context)
    
    masked_to_email = mask_email(user.email)
    
    try:
        email_message = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
        email_message.attach_alternative(html_email, "text/html")
        email_message.send()

        DailyReminderLog.objects.create(user=user, date=today)
        logger.info(f"[LEMBRETE] Sucesso ao enviar e logar para {masked_to_email}")
        
    except Exception as e:
        logger.error(f"[LEMBRETE] Erro ao enviar para {masked_to_email}: {str(e)}")
        raise
