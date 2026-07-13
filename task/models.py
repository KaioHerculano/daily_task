from datetime import timedelta

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone


class TaskDayManager(models.Manager):

    def get_monthly_study_counts(self, user, start_year, end_year):
        return (
            self.filter(user=user, date__year__gte=start_year, date__year__lte=end_year)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )


class TaskDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    objects = TaskDayManager()

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class DailyReminderLog(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reminder_logs"
    )
    date = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = ("user", "date")
        verbose_name = "Log de Lembrete Diário"


class Subject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default="#000000")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Topic(models.Model):
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="topics"
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.subject.name}"


class StudySession(models.Model):

    class ObjectiveAchieved(models.TextChoices):
        YES = ("YES", "Yes")
        PARTIAL = ("PARTIAL", "Partial")
        NO = ("NO", "No")
        PENDING = ("PENDING", "Pending")

    class Mode(models.TextChoices):
        FREE = ("FREE", "Free")
        POMODORO = ("POMODORO", "Pomodoro")

    class Status(models.TextChoices):
        IN_PROGRESS = ("IN_PROGRESS", "In Progress")
        PAUSED = ("PAUSED", "Paused")
        COMPLETED = ("COMPLETED", "Completed")
        ABANDONED = ("ABANDONED", "Abandoned")

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="study_sessions"
    )
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="sessions")
    objective_text = models.CharField(max_length=255)
    objective_achieved = models.CharField(
        max_length=10,
        choices=ObjectiveAchieved.choices,
        default=ObjectiveAchieved.PENDING,
    )
    objective_result = models.TextField(blank=True)
    learning_note = models.TextField(blank=True)
    next_step = models.CharField(max_length=255, blank=True)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.FREE)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.IN_PROGRESS
    )
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    focus_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True
    )

    def __str__(self):
        return f"Session {self.id} - {self.topic.name}"

    @property
    def gross_time(self):
        if not self.start_time:
            return timedelta(0)
        end = self.end_time or timezone.now()
        return end - self.start_time

    @property
    def paused_time(self):
        total_pause = timedelta(0)
        for pause in self.pauses.all():
            pause_end = pause.pause_end or timezone.now()
            if pause.pause_start:
                total_pause += pause_end - pause.pause_start
        return total_pause

    @property
    def net_time(self):
        return self.gross_time - self.paused_time


class SessionPause(models.Model):
    session = models.ForeignKey(
        StudySession, on_delete=models.CASCADE, related_name="pauses"
    )
    pause_start = models.DateTimeField(default=timezone.now)
    pause_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pause for {self.session.id}"
