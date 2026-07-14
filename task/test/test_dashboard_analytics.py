from datetime import timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from faker import Faker

from task.models import SessionPause, StudySession, Subject, Topic
from task.services import get_delayed_topics, get_weekly_net_time

fake = Faker()


class DashboardAnalyticsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name="Math")
        self.topic = Topic.objects.create(subject=self.subject, name="Algebra")
        self.client.force_login(self.user)

    def test_weekly_net_time_subtracts_pauses(self):
        start_time = timezone.now() - timedelta(hours=2)
        session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text="Study equations",
            objective_result="Finished examples.",
            learning_note="Factoring needs practice.",
            start_time=start_time,
            end_time=start_time + timedelta(hours=2),
            status=StudySession.Status.COMPLETED,
        )
        SessionPause.objects.create(
            session=session,
            pause_start=start_time + timedelta(minutes=30),
            pause_end=start_time + timedelta(minutes=45),
        )

        data = get_weekly_net_time(self.user)

        self.assertEqual(data["weekly_net_time_values"][-1], 1.75)

    def test_delayed_topics_returns_topics_without_recent_session(self):
        delayed_topic = Topic.objects.create(subject=self.subject, name="Geometry")
        start_time = timezone.now() - timedelta(days=1)
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text="Study equations",
            objective_result="Done.",
            learning_note="Clear.",
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
            status=StudySession.Status.COMPLETED,
        )

        topics = list(get_delayed_topics(self.user))

        self.assertIn(delayed_topic, topics)
        self.assertNotIn(self.topic, topics)

    def test_dashboard_query_count_is_stable(self):
        for index in range(3):
            Topic.objects.create(subject=self.subject, name=f"Topic {index}")

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 18)
