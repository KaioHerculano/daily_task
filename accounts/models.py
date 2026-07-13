from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    weekly_goal = models.PositiveIntegerField(
        default=5, verbose_name="Meta Semanal (dias)"
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"
