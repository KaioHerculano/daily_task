from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from faker import Faker

from task.models import StudySession, Subject, Topic
from task.study_services import start_session

fake = Faker()


class SessionViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name=fake.word())
        self.topic = Topic.objects.create(subject=self.subject, name=fake.word())
        self.client.force_login(self.user)

    def test_cancel_session_view(self):
        session = start_session(self.user, self.topic.id, "Test Objective")
        url = reverse("cancel_session")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "cancelled"})
        self.assertFalse(StudySession.objects.filter(id=session.id).exists())

    def test_cancel_session_view_fails_when_no_active_session(self):
        url = reverse("cancel_session")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())


class TopicViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name=fake.word())
        self.topic = Topic.objects.create(subject=self.subject, name="Original Name")
        self.client.force_login(self.user)

    def test_update_topic_view_success(self):
        url = reverse("update_topic", kwargs={"pk": self.topic.pk})
        response = self.client.post(url, {"name": "Updated Name", "priority": "HIGH"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.name, "Updated Name")
        self.assertEqual(self.topic.priority, Topic.Priority.HIGH)

    def test_update_topic_view_error_redirects(self):
        url = reverse("update_topic", kwargs={"pk": self.topic.pk})
        response = self.client.post(url, {"name": "   ", "priority": "HIGH"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.name, "Original Name")

    def test_update_topic_view_requires_login(self):
        self.client.logout()
        url = reverse("update_topic", kwargs={"pk": self.topic.pk})
        response = self.client.post(url, {"name": "Updated Name", "priority": "HIGH"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class WeeklyPlanGenerateViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name="Science")
        self.topic = Topic.objects.create(subject=self.subject, name="Biology")
        self.url = reverse("generate_weekly_plan")
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    def test_generate_weekly_plan_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    @patch("task.views.generate_weekly_plan_with_ai")
    def test_generate_weekly_plan_success_ajax(self, mock_generate):
        mock_plan = MagicMock(id=42)
        mock_generate.return_value = mock_plan

        response = self.client.post(
            self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "success", "message": "Plano semanal gerado com sucesso!", "plan_id": 42},
        )
        mock_generate.assert_called_once_with(self.user, force_refresh=True)

    @patch("task.views.generate_weekly_plan_with_ai")
    def test_generate_weekly_plan_success_standard_redirect(self, mock_generate):
        mock_plan = MagicMock(id=42)
        mock_generate.return_value = mock_plan

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    @patch("task.views.generate_weekly_plan_with_ai")
    def test_generate_weekly_plan_no_topics_ajax(self, mock_generate):
        mock_generate.return_value = None

        response = self.client.post(
            self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")

    @patch("task.views.generate_weekly_plan_with_ai")
    def test_generate_weekly_plan_no_topics_standard_redirect(self, mock_generate):
        mock_generate.return_value = None

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    @patch("task.views.generate_weekly_plan_with_ai")
    def test_generate_weekly_plan_rate_limit_ajax(self, mock_generate):
        mock_plan = MagicMock(id=42)
        mock_generate.return_value = mock_plan

        response1 = self.client.post(
            self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response1.status_code, 200)

        response2 = self.client.post(
            self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response2.status_code, 429)
        self.assertEqual(response2.json()["status"], "error")

    @patch("task.views.generate_weekly_plan_with_ai")
    def test_generate_weekly_plan_rate_limit_standard_redirect(self, mock_generate):
        mock_plan = MagicMock(id=42)
        mock_generate.return_value = mock_plan

        self.client.post(self.url)
        response2 = self.client.post(self.url)
        self.assertEqual(response2.status_code, 302)
        self.assertEqual(response2.url, reverse("dashboard"))

