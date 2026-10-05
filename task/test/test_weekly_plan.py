from datetime import date, datetime, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from task.exceptions import InvalidPlanItemError
from task.models import Subject, Topic, WeeklyPlan, WeeklyPlanItem
from task.services import (
    create_weekly_plan,
    get_current_week_plan,
    toggle_plan_item_status,
)


class WeeklyPlanModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="planner_user", password="password")
        self.week_start = date(2026, 10, 5)
        self.week_end = date(2026, 10, 11)

    def test_create_weekly_plan_success(self):
        plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=self.week_start,
            week_end=self.week_end,
        )
        self.assertEqual(plan.user, self.user)
        self.assertEqual(plan.week_start, self.week_start)
        self.assertEqual(plan.week_end, self.week_end)
        self.assertIsNotNone(plan.created_at)
        self.assertIn("WeeklyPlan planner_user (2026-10-05 - 2026-10-11)", str(plan))

    def test_weekly_plan_unique_together_user_and_week_start(self):
        WeeklyPlan.objects.create(
            user=self.user,
            week_start=self.week_start,
            week_end=self.week_end,
        )
        with self.assertRaises(IntegrityError):
            WeeklyPlan.objects.create(
                user=self.user,
                week_start=self.week_start,
                week_end=self.week_end + timedelta(days=1),
            )

    def test_different_users_can_have_plan_same_week(self):
        other_user = User.objects.create_user(username="other_user", password="password")
        plan1 = WeeklyPlan.objects.create(
            user=self.user,
            week_start=self.week_start,
            week_end=self.week_end,
        )
        plan2 = WeeklyPlan.objects.create(
            user=other_user,
            week_start=self.week_start,
            week_end=self.week_end,
        )
        self.assertNotEqual(plan1.id, plan2.id)


class WeeklyPlanItemModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="item_user", password="password")
        self.subject = Subject.objects.create(user=self.user, name="Mathematics")
        self.topic = Topic.objects.create(subject=self.subject, name="Calculus")
        self.plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=date(2026, 10, 5),
            week_end=date(2026, 10, 11),
        )

    def test_create_weekly_plan_item_default_values(self):
        item = WeeklyPlanItem.objects.create(
            plan=self.plan,
            day_of_week=WeeklyPlanItem.DayOfWeek.MONDAY,
            topic=self.topic,
        )
        self.assertEqual(item.duration_minutes, 60)
        self.assertFalse(item.is_completed)
        self.assertIsNone(item.completed_at)
        self.assertEqual(item.order, 0)
        self.assertEqual(item.day_of_week, 0)
        self.assertEqual(item.get_day_of_week_display(), "Segunda-feira")
        self.assertEqual(
            str(item),
            f"{self.user.username} - Segunda-feira - Calculus",
        )

    def test_day_of_week_choices_and_display(self):
        days_expected = [
            (WeeklyPlanItem.DayOfWeek.MONDAY, "Segunda-feira"),
            (WeeklyPlanItem.DayOfWeek.TUESDAY, "Terça-feira"),
            (WeeklyPlanItem.DayOfWeek.WEDNESDAY, "Quarta-feira"),
            (WeeklyPlanItem.DayOfWeek.THURSDAY, "Quinta-feira"),
            (WeeklyPlanItem.DayOfWeek.FRIDAY, "Sexta-feira"),
            (WeeklyPlanItem.DayOfWeek.SATURDAY, "Sábado"),
            (WeeklyPlanItem.DayOfWeek.SUNDAY, "Domingo"),
        ]
        for val, display in days_expected:
            item = WeeklyPlanItem(
                plan=self.plan,
                day_of_week=val,
                topic=self.topic,
            )
            self.assertEqual(item.get_day_of_week_display(), display)

    def test_validation_day_of_week_bounds(self):
        invalid_item_low = WeeklyPlanItem(
            plan=self.plan,
            day_of_week=-1,
            topic=self.topic,
        )
        with self.assertRaises(ValidationError):
            invalid_item_low.full_clean()

        invalid_item_high = WeeklyPlanItem(
            plan=self.plan,
            day_of_week=7,
            topic=self.topic,
        )
        with self.assertRaises(ValidationError):
            invalid_item_high.full_clean()

    def test_validation_duration_minutes_bounds(self):
        invalid_low = WeeklyPlanItem(
            plan=self.plan,
            day_of_week=0,
            topic=self.topic,
            duration_minutes=14,
        )
        with self.assertRaises(ValidationError):
            invalid_low.full_clean()

        invalid_high = WeeklyPlanItem(
            plan=self.plan,
            day_of_week=0,
            topic=self.topic,
            duration_minutes=1441,
        )
        with self.assertRaises(ValidationError):
            invalid_high.full_clean()

        valid_item = WeeklyPlanItem(
            plan=self.plan,
            day_of_week=0,
            topic=self.topic,
            duration_minutes=120,
        )
        valid_item.full_clean()


class WeeklyPlanServicesTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="service_user", password="password")
        self.other_user = User.objects.create_user(username="other_service_user", password="password")
        self.subject = Subject.objects.create(user=self.user, name="Physics")
        self.topic1 = Topic.objects.create(subject=self.subject, name="Mechanics")
        self.topic2 = Topic.objects.create(subject=self.subject, name="Thermodynamics")

        self.week_start = date(2026, 10, 5)
        self.week_end = date(2026, 10, 11)
        self.plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=self.week_start,
            week_end=self.week_end,
        )
        self.item = WeeklyPlanItem.objects.create(
            plan=self.plan,
            day_of_week=WeeklyPlanItem.DayOfWeek.MONDAY,
            topic=self.topic1,
            duration_minutes=45,
            order=1,
        )

    def test_toggle_plan_item_status_to_completed(self):
        self.assertFalse(self.item.is_completed)
        self.assertIsNone(self.item.completed_at)

        toggled = toggle_plan_item_status(self.user, self.item.id)
        self.assertTrue(toggled.is_completed)
        self.assertIsNotNone(toggled.completed_at)

        self.item.refresh_from_db()
        self.assertTrue(self.item.is_completed)
        self.assertIsNotNone(self.item.completed_at)

    def test_toggle_plan_item_status_back_to_uncompleted(self):
        self.item.is_completed = True
        self.item.completed_at = timezone.now()
        self.item.save()

        toggled = toggle_plan_item_status(self.user, self.item.id)
        self.assertFalse(toggled.is_completed)
        self.assertIsNone(toggled.completed_at)

        self.item.refresh_from_db()
        self.assertFalse(self.item.is_completed)
        self.assertIsNone(self.item.completed_at)

    def test_toggle_plan_item_status_unauthorized_user(self):
        with self.assertRaises(InvalidPlanItemError):
            toggle_plan_item_status(self.other_user, self.item.id)

    def test_toggle_plan_item_status_non_existent(self):
        with self.assertRaises(InvalidPlanItemError):
            toggle_plan_item_status(self.user, 999999)

    def test_get_current_week_plan_with_specific_date(self):
        mid_week_date = date(2026, 10, 7)
        plan = get_current_week_plan(self.user, reference_date=mid_week_date)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.id, self.plan.id)
        self.assertEqual(plan.week_start, self.week_start)

        items = list(plan.items.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].topic.name, "Mechanics")
        self.assertEqual(items[0].topic.subject.name, "Physics")

    def test_get_current_week_plan_with_datetime(self):
        dt = datetime(2026, 10, 8, 14, 30, tzinfo=timezone.get_current_timezone())
        plan = get_current_week_plan(self.user, reference_date=dt)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.id, self.plan.id)

    def test_get_current_week_plan_none_when_no_plan(self):
        different_week = date(2026, 11, 2)
        plan = get_current_week_plan(self.user, reference_date=different_week)
        self.assertIsNone(plan)

    def test_get_current_week_plan_default_reference_date(self):
        dedicated_user = User.objects.create_user(
            username="dedicated_plan_user", password="password"
        )
        today = timezone.localdate()
        today_start = today - timedelta(days=today.weekday())
        current_plan = WeeklyPlan.objects.create(
            user=dedicated_user,
            week_start=today_start,
            week_end=today_start + timedelta(days=6),
        )
        plan = get_current_week_plan(dedicated_user)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.id, current_plan.id)

    def test_create_weekly_plan_with_items(self):
        target_start = date(2026, 10, 12)
        items_payload = [
            {
                "day_of_week": WeeklyPlanItem.DayOfWeek.MONDAY,
                "topic": self.topic1,
                "duration_minutes": 60,
                "order": 1,
            },
            {
                "day_of_week": WeeklyPlanItem.DayOfWeek.TUESDAY,
                "topic": self.topic2,
                "duration_minutes": 90,
                "order": 1,
            },
        ]
        created = create_weekly_plan(self.user, target_start, items_data=items_payload)
        self.assertEqual(created.user, self.user)
        self.assertEqual(created.week_start, target_start)
        self.assertEqual(created.week_end, target_start + timedelta(days=6))
        self.assertEqual(created.items.count(), 2)

    def test_format_duration_minutes(self):
        from task.services import format_duration_minutes

        self.assertEqual(format_duration_minutes(0), "0min")
        self.assertEqual(format_duration_minutes(45), "45min")
        self.assertEqual(format_duration_minutes(60), "1h")
        self.assertEqual(format_duration_minutes(75), "1h15min")
        self.assertEqual(format_duration_minutes(125), "2h05min")

    def test_get_weekly_plan_context_with_plan(self):
        from task.services import get_weekly_plan_context

        context = get_weekly_plan_context(self.user, reference_date=self.week_start)
        self.assertEqual(context["weekly_plan"], self.plan)
        self.assertEqual(len(context["weekly_plan_days"]), 7)
        self.assertEqual(context["weekly_plan_total_planned_minutes"], 45)
        self.assertEqual(context["weekly_plan_total_completed_minutes"], 0)
        self.assertEqual(context["weekly_plan_completion_percentage"], 0)
        self.assertEqual(context["weekly_plan_total_planned_label"], "45min")
        self.assertEqual(context["weekly_plan_total_completed_label"], "0min")
        self.assertEqual(context["weekly_plan_total_items"], 1)
        self.assertEqual(context["weekly_plan_completed_items"], 0)

        monday_data = context["weekly_plan_days"][0]
        self.assertEqual(monday_data["day_name"], "Segunda-feira")
        self.assertEqual(monday_data["planned_minutes"], 45)
        self.assertEqual(len(monday_data["items"]), 1)

    def test_get_weekly_plan_context_without_plan(self):
        from task.services import get_weekly_plan_context

        no_plan_user = User.objects.create_user(
            username="no_plan_user", password="password"
        )
        context = get_weekly_plan_context(no_plan_user)
        self.assertIsNone(context["weekly_plan"])
        self.assertEqual(len(context["weekly_plan_days"]), 7)
        self.assertEqual(context["weekly_plan_total_planned_minutes"], 0)
        self.assertEqual(context["weekly_plan_total_completed_minutes"], 0)
        self.assertEqual(context["weekly_plan_completion_percentage"], 0)

