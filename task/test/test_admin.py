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
    WeeklyPlan,
    WeeklyPlanItem,
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
            WeeklyPlan,
            WeeklyPlanItem,
        ]

        for model in models_to_check:
            self.assertIn(
                model,
                admin.site._registry,
                f"Model {model.__name__} is not registered in admin.",
            )

    def test_topic_admin_priority_fields(self):
        topic_admin = admin.site._registry[Topic]
        self.assertIn("priority", topic_admin.list_display)
        self.assertIn("priority", topic_admin.list_filter)
        self.assertIn("priority", topic_admin.list_editable)

    def test_weekly_plan_admin_configuration(self):
        plan_admin = admin.site._registry[WeeklyPlan]
        self.assertIn("user", plan_admin.list_display)
        self.assertIn("week_start", plan_admin.list_display)
        self.assertIn("week_end", plan_admin.list_display)

    def test_weekly_plan_item_admin_configuration(self):
        item_admin = admin.site._registry[WeeklyPlanItem]
        self.assertIn("plan", item_admin.list_display)
        self.assertIn("day_of_week", item_admin.list_display)
        self.assertIn("topic", item_admin.list_display)
        self.assertIn("is_completed", item_admin.list_editable)

