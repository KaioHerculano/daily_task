from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class PreferredStudyTime(models.TextChoices):
        MORNING = "MORNING", "Morning"
        EVENING = "EVENING", "Evening"
        NIGHT = "NIGHT", "Night"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    weekly_goal = models.PositiveIntegerField(
        default=5, verbose_name="Meta Semanal (dias)"
    )
    weekly_goal_hours = models.PositiveIntegerField(default=10)
    timezone = models.CharField(max_length=50, default="UTC")
    preferred_study_time = models.CharField(
        max_length=10,
        choices=PreferredStudyTime.choices,
        default=PreferredStudyTime.MORNING,
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"
