from django.contrib import admin
from django.test import TestCase

from task.models import (
    DailyReminderLog,
    SessionPause,
    StudyInsight,
    StudySession,
    Subject,
    TaskDay,
    Topic,
)


class AdminRegistrationTest(TestCase):
    def test_models_are_registered_in_admin(self):
        models_to_check = [
            StudySession,
            Subject,
            Topic,
            TaskDay,
            DailyReminderLog,
            StudyInsight,
            SessionPause,
        ]

        for model in models_to_check:
            self.assertIn(
                model,
                admin.site._registry,
                f"Model {model.__name__} is not registered in admin.",
            )
