import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from task.ai_services import (
    PlannerContext,
    build_deterministic_weekly_plan,
    build_planner_context,
    can_reuse_previous_plan,
    generate_weekly_plan_with_ai,
    get_user_pending_topics,
    persist_weekly_plan,
    replicate_weekly_plan,
    try_generate_with_ai,
    try_reuse_previous_plan,
)
from task.models import Subject, Topic, WeeklyPlan, WeeklyPlanItem
from task.prompts.weekly_planner import (
    PlannedItemDTO,
    build_weekly_planner_prompt,
    validate_weekly_planner_response,
)


class PlannedItemDTOTest(TestCase):

    def test_parse_valid_dict(self):
        item = PlannedItemDTO.parse(
            {"day_of_week": 2, "topic_id": 5, "duration_minutes": 45, "order": 1},
            valid_topic_ids={5},
        )
        self.assertIsNotNone(item)
        self.assertEqual(item.day_of_week, 2)
        self.assertEqual(item.topic_id, 5)
        self.assertEqual(item.duration_minutes, 45)
        self.assertEqual(item.order, 1)

    def test_parse_invalid_types_or_values(self):
        self.assertIsNone(PlannedItemDTO.parse("not_a_dict", {5}))
        self.assertIsNone(
            PlannedItemDTO.parse(
                {"day_of_week": 7, "topic_id": 5, "duration_minutes": 60}, {5}
            )
        )
        self.assertIsNone(
            PlannedItemDTO.parse(
                {"day_of_week": 0, "topic_id": 99, "duration_minutes": 60}, {5}
            )
        )
        self.assertIsNone(
            PlannedItemDTO.parse(
                {"day_of_week": 0, "topic_id": 5, "duration_minutes": 10}, {5}
            )
        )


class WeeklyPlannerPromptTest(TestCase):

    def test_build_weekly_planner_prompt(self):
        prompt_str = build_weekly_planner_prompt(
            username="student1",
            topics_payload=[{"id": 1, "name": "Calculus", "priority": "HIGH"}],
            weekday_minutes=90,
            weekend_minutes=120,
            week_start=date(2026, 10, 5),
            week_end=date(2026, 10, 11),
        )
        data = json.loads(prompt_str)
        self.assertEqual(data["student"], "student1")
        self.assertEqual(data["daily_budget_minutes"]["weekday"], 90)
        self.assertEqual(data["daily_budget_minutes"]["weekend"], 120)
        self.assertEqual(data["period"]["week_start"], "2026-10-05")
        self.assertEqual(data["period"]["week_end"], "2026-10-11")
        self.assertEqual(len(data["topics"]), 1)

    def test_validate_weekly_planner_response_success(self):
        valid_response = {
            "plan": [
                {
                    "day_of_week": 0,
                    "topic_id": 10,
                    "duration_minutes": 60,
                    "order": 1,
                },
                {
                    "day_of_week": 1,
                    "topic_id": 20,
                    "duration_minutes": 45,
                    "order": 1,
                },
            ]
        }
        validated = validate_weekly_planner_response(valid_response, {10, 20})
        self.assertEqual(len(validated), 2)
        self.assertEqual(validated[0]["day_of_week"], 0)
        self.assertEqual(validated[0]["topic_id"], 10)
        self.assertEqual(validated[0]["duration_minutes"], 60)

    def test_validate_weekly_planner_response_deduplicates(self):
        response_with_duplicates = {
            "plan": [
                {
                    "day_of_week": 0,
                    "topic_id": 10,
                    "duration_minutes": 60,
                    "order": 1,
                },
                {
                    "day_of_week": 0,
                    "topic_id": 10,
                    "duration_minutes": 60,
                    "order": 2,
                },
            ]
        }
        validated = validate_weekly_planner_response(response_with_duplicates, {10})
        self.assertEqual(len(validated), 1)

    def test_validate_weekly_planner_response_invalid_structure(self):
        with self.assertRaises(ValueError):
            validate_weekly_planner_response([], {10})

        with self.assertRaises(ValueError):
            validate_weekly_planner_response({"plan": "not_a_list"}, {10})

        with self.assertRaises(ValueError):
            validate_weekly_planner_response({"plan": []}, {10})

    def test_validate_weekly_planner_response_no_valid_items(self):
        with self.assertRaises(ValueError):
            validate_weekly_planner_response(
                {"plan": [{"day_of_week": 99, "topic_id": 10, "duration_minutes": 60}]},
                {10},
            )


class WeeklyPlannerServiceTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="planner_user", password="password")
        self.subject = Subject.objects.create(user=self.user, name="Engineering")
        self.topic_high = Topic.objects.create(
            subject=self.subject, name="Algorithms", priority=Topic.Priority.HIGH
        )
        self.topic_med = Topic.objects.create(
            subject=self.subject, name="Databases", priority=Topic.Priority.MEDIUM
        )
        self.week_start = date(2026, 10, 5)

    def test_get_user_pending_topics_orders_by_priority(self):
        topic_low = Topic.objects.create(
            subject=self.subject, name="Intro", priority=Topic.Priority.LOW
        )
        topics = list(get_user_pending_topics(self.user))
        self.assertEqual(topics[0].id, self.topic_high.id)
        self.assertEqual(topics[1].id, self.topic_med.id)
        self.assertEqual(topics[2].id, topic_low.id)

    def test_get_user_pending_topics_ignores_completed(self):
        self.topic_med.completed_at = timezone.now()
        self.topic_med.completion_summary = "Done"
        self.topic_med.save()
        topics = list(get_user_pending_topics(self.user))
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0].id, self.topic_high.id)

    def test_build_planner_context(self):
        context = build_planner_context(self.user, self.week_start)
        self.assertEqual(context.user, self.user)
        self.assertEqual(context.week_start, self.week_start)
        self.assertEqual(len(context.high_priority_topics), 1)
        self.assertEqual(len(context.other_topics), 1)
        self.assertTrue(context.has_topics)
        self.assertEqual(context.valid_topic_ids, {self.topic_high.id, self.topic_med.id})

    def test_build_deterministic_weekly_plan_allocates_high_priority_every_day(self):
        context = build_planner_context(self.user, self.week_start)
        items = build_deterministic_weekly_plan(context)
        days_with_high = {
            item["day_of_week"]
            for item in items
            if item["topic_id"] == self.topic_high.id
        }
        self.assertEqual(days_with_high, {0, 1, 2, 3, 4, 5, 6})

    def test_build_deterministic_weekly_plan_allocates_other_topics_in_remaining_time(self):
        context = build_planner_context(self.user, self.week_start)
        items = build_deterministic_weekly_plan(context)
        med_items = [
            item for item in items if item["topic_id"] == self.topic_med.id
        ]
        self.assertGreater(len(med_items), 0)

    def test_can_reuse_previous_plan_true_when_topics_match(self):
        prev_start = self.week_start - timedelta(days=7)
        prev_plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=prev_start,
            week_end=prev_start + timedelta(days=6),
        )
        WeeklyPlanItem.objects.create(
            plan=prev_plan,
            day_of_week=0,
            topic=self.topic_high,
            duration_minutes=60,
        )
        WeeklyPlanItem.objects.create(
            plan=prev_plan,
            day_of_week=1,
            topic=self.topic_med,
            duration_minutes=60,
        )
        topics = [self.topic_high, self.topic_med]
        self.assertTrue(can_reuse_previous_plan(self.user, prev_plan, topics))

    def test_can_reuse_previous_plan_false_when_topics_differ(self):
        prev_start = self.week_start - timedelta(days=7)
        prev_plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=prev_start,
            week_end=prev_start + timedelta(days=6),
        )
        WeeklyPlanItem.objects.create(
            plan=prev_plan,
            day_of_week=0,
            topic=self.topic_high,
            duration_minutes=60,
        )
        topics = [self.topic_high, self.topic_med]
        self.assertFalse(can_reuse_previous_plan(self.user, prev_plan, topics))

    def test_replicate_weekly_plan_resets_completion(self):
        prev_start = self.week_start - timedelta(days=7)
        prev_plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=prev_start,
            week_end=prev_start + timedelta(days=6),
        )
        WeeklyPlanItem.objects.create(
            plan=prev_plan,
            day_of_week=0,
            topic=self.topic_high,
            duration_minutes=60,
            is_completed=True,
            completed_at=timezone.now(),
        )
        replicated = replicate_weekly_plan(prev_plan, self.week_start)
        self.assertEqual(replicated.week_start, self.week_start)
        items = list(replicated.items.all())
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0].is_completed)
        self.assertIsNone(items[0].completed_at)

    def test_try_reuse_previous_plan_respects_force_refresh(self):
        context = build_planner_context(self.user, self.week_start)
        self.assertIsNone(try_reuse_previous_plan(context, force_refresh=True))

    def test_generate_weekly_plan_returns_none_when_no_topics(self):
        Topic.objects.all().delete()
        plan = generate_weekly_plan_with_ai(self.user, self.week_start)
        self.assertIsNone(plan)

    def test_generate_weekly_plan_returns_existing_plan(self):
        existing = WeeklyPlan.objects.create(
            user=self.user,
            week_start=self.week_start,
            week_end=self.week_start + timedelta(days=6),
        )
        WeeklyPlanItem.objects.create(
            plan=existing,
            day_of_week=0,
            topic=self.topic_high,
            duration_minutes=60,
        )
        plan = generate_weekly_plan_with_ai(self.user, self.week_start)
        self.assertEqual(plan.id, existing.id)

    @override_settings(
        AI_PROVIDER="openrouter",
        AI_MODEL="test-model",
        AI_APP_NAME="test-app",
        AI_SITE_URL="http://testserver",
        AI_REQUEST_TIMEOUT=30,
        OPENROUTER_API_KEY="test-key",
        OPENROUTER_API_URL="http://provider.test",
    )
    @patch("task.ai_providers.request.urlopen")
    def test_generate_weekly_plan_with_ai_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "plan": [
                                        {
                                            "day_of_week": 0,
                                            "topic_id": self.topic_high.id,
                                            "duration_minutes": 60,
                                            "order": 1,
                                        },
                                        {
                                            "day_of_week": 1,
                                            "topic_id": self.topic_med.id,
                                            "duration_minutes": 60,
                                            "order": 1,
                                        },
                                    ]
                                }
                            )
                        }
                    }
                ]
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        plan = generate_weekly_plan_with_ai(self.user, self.week_start)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.items.count(), 2)
        self.assertTrue(mock_urlopen.called)

    @override_settings(
        AI_PROVIDER="openrouter",
        AI_MODEL="test-model",
        AI_APP_NAME="test-app",
        AI_SITE_URL="http://testserver",
        AI_REQUEST_TIMEOUT=30,
        OPENROUTER_API_KEY="test-key",
        OPENROUTER_API_URL="http://provider.test",
    )
    @patch("task.ai_providers.request.urlopen")
    def test_generate_weekly_plan_reaps_previous_plan_without_ai(self, mock_urlopen):
        prev_start = self.week_start - timedelta(days=7)
        prev_plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=prev_start,
            week_end=prev_start + timedelta(days=6),
        )
        WeeklyPlanItem.objects.create(
            plan=prev_plan,
            day_of_week=0,
            topic=self.topic_high,
            duration_minutes=60,
        )
        WeeklyPlanItem.objects.create(
            plan=prev_plan,
            day_of_week=1,
            topic=self.topic_med,
            duration_minutes=60,
        )

        plan = generate_weekly_plan_with_ai(self.user, self.week_start)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.week_start, self.week_start)
        self.assertEqual(plan.items.count(), 2)
        self.assertFalse(mock_urlopen.called)

    @override_settings(
        AI_PROVIDER="openrouter",
        AI_MODEL="test-model",
        AI_APP_NAME="test-app",
        AI_SITE_URL="http://testserver",
        AI_REQUEST_TIMEOUT=30,
        OPENROUTER_API_KEY="test-key",
        OPENROUTER_API_URL="http://provider.test",
    )
    @patch("task.ai_providers.request.urlopen")
    def test_generate_weekly_plan_fallback_on_ai_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("Connection timed out")

        plan = generate_weekly_plan_with_ai(self.user, self.week_start)

        self.assertIsNotNone(plan)
        self.assertGreater(plan.items.count(), 0)
        self.assertTrue(mock_urlopen.called)

    @override_settings(
        AI_PROVIDER="openrouter",
        AI_MODEL="test-model",
        AI_APP_NAME="test-app",
        AI_SITE_URL="http://testserver",
        AI_REQUEST_TIMEOUT=30,
        OPENROUTER_API_KEY="test-key",
        OPENROUTER_API_URL="http://provider.test",
    )
    @patch("task.ai_providers.request.urlopen")
    def test_generate_weekly_plan_fallback_on_invalid_json(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "Not a json response"
                        }
                    }
                ]
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        plan = generate_weekly_plan_with_ai(self.user, self.week_start)

        self.assertIsNotNone(plan)
        self.assertGreater(plan.items.count(), 0)
        self.assertTrue(mock_urlopen.called)
