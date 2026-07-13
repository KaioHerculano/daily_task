from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


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


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
