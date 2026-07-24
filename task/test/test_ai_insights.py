import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from faker import Faker

from task.ai_services import (
    build_weekly_study_payload,
    generate_weekly_insight_for_user,
)
from task.models import StudyInsight, StudySession, Subject, Topic

fake = Faker()


class StudyInsightTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name="Physics")
        self.topic = Topic.objects.create(subject=self.subject, name="Kinematics")
        start_time = timezone.now() - timedelta(hours=1)
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text="Understand velocity.",
            objective_achieved=StudySession.ObjectiveAchieved.YES,
            objective_result="Solved velocity exercises.",
            learning_note="Graphs need attention.",
            next_step="Practice graph reading.",
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
            status=StudySession.Status.COMPLETED,
        )

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
    def test_generate_weekly_insight_calls_openrouter_and_saves_result(
        self, mock_urlopen
    ):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Good week.",
                                    "strengths": "Clear objectives.",
                                    "risks": "Graph interpretation.",
                                    "next_actions": "Review charts.",
                                }
                            )
                        }
                    }
                ]
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        insight = generate_weekly_insight_for_user(self.user)

        self.assertEqual(insight.summary, "Good week.")
        self.assertEqual(insight.strengths, "Clear objectives.")
        self.assertEqual(StudyInsight.objects.count(), 1)
        self.assertTrue(mock_urlopen.called)

    @patch("task.management.commands.generate_insights.generate_weekly_insights")
    def test_generate_insights_command_uses_service(self, mock_generate):
        mock_generate.return_value = [MagicMock()]

        call_command("generate_insights")

        mock_generate.assert_called_once_with()

    @patch("task.tasks.generate_weekly_insights")
    def test_weekly_insight_task_uses_previous_week_reference(self, mock_generate):
        from task.tasks import generate_weekly_study_insights

        mock_generate.return_value = [MagicMock(), MagicMock()]

        result = generate_weekly_study_insights()

        self.assertEqual(result, 2)
        mock_generate.assert_called_once_with(
            reference_date=timezone.localdate() - timedelta(days=1)
        )

    def test_ai_payload_includes_sessions_from_completed_topics(self):
        self.topic.completed_at = timezone.now()
        self.topic.completion_summary = "Completed after routing practice."
        self.topic.save(update_fields=["completed_at", "completion_summary"])
        week_start = timezone.localdate() - timedelta(
            days=timezone.localdate().weekday()
        )
        week_end = week_start + timedelta(days=6)

        payload = build_weekly_study_payload(self.user, week_start, week_end)

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["topic"], self.topic.name)
        self.assertEqual(payload[0]["learning_note"], "Graphs need attention.")
