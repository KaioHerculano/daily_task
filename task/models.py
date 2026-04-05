from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone


class TaskDayManager(models.Manager):
    def get_monthly_study_counts(self, user, start_year, end_year):
        return self.filter(
            user=user,
            date__year__gte=start_year,
            date__year__lte=end_year,
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Count('id')
        ).order_by('month')


class TaskDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    
    objects = TaskDayManager()

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.username} - {self.date}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    weekly_goal = models.PositiveIntegerField(default=5, verbose_name="Meta Semanal (dias)")

    def __str__(self):
        return f"Perfil de {self.user.username}"


class DailyReminderLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminder_logs')
    date = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = ('user', 'date') 
        verbose_name = "Log de Lembrete Diário"