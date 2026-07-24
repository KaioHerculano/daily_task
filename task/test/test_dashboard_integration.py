from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from faker import Faker

from task.models import StudySession, Subject, Topic

fake = Faker()


class DashboardIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.other_user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name=fake.word())
        self.topic = Topic.objects.create(subject=self.subject, name=fake.word())
        self.client.force_login(self.user)

    def test_dashboard_context_includes_study_domain_data(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.subject, response.context["subjects"])
        self.assertIn("subject_form", response.context)
        self.assertIn("topic_form", response.context)

    def test_create_subject_attaches_logged_user(self):
        response = self.client.post(
            reverse("create_subject"),
            {"name": "Physics", "color": "#336699"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(
            Subject.objects.filter(
                user=self.user, name="Physics", color="#336699"
            ).exists()
        )

    def test_create_topic_attaches_to_owned_subject(self):
        response = self.client.post(
            reverse("create_topic"),
            {"subject": self.subject.id, "name": "Kinematics"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(
            Topic.objects.filter(subject=self.subject, name="Kinematics").exists()
        )

    def test_create_topic_rejects_subject_from_another_user(self):
        other_subject = Subject.objects.create(user=self.other_user, name=fake.word())
        response = self.client.post(
            reverse("create_topic"),
            {"subject": other_subject.id, "name": "Private Topic"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Topic.objects.filter(name="Private Topic").exists())

    def test_start_session_rejects_topic_from_another_user(self):
        other_subject = Subject.objects.create(user=self.other_user, name=fake.word())
        other_topic = Topic.objects.create(subject=other_subject, name=fake.word())
        response = self.client.post(
            reverse("start_session"),
            {"topic_id": other_topic.id, "objective_text": "Study"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudySession.objects.count(), 0)

    def test_start_session_requires_objective(self):
        response = self.client.post(
            reverse("start_session"),
            {"topic_id": self.topic.id},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudySession.objects.count(), 0)

    def test_stop_session_requires_journal_fields(self):
        session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text="Study vectors",
            status=StudySession.Status.IN_PROGRESS,
        )
        response = self.client.post(
            reverse("stop_session"),
            {
                "objective_achieved": "PARTIAL",
                "objective_result": "Solved basic exercises.",
                "learning_note": "Need more practice with projections.",
                "next_step": "Review examples tomorrow.",
            },
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, StudySession.Status.COMPLETED)
        self.assertEqual(session.objective_achieved, "PARTIAL")
        self.assertEqual(session.learning_note, "Need more practice with projections.")

    def test_delete_topic_without_history_removes_record(self):
        topic = Topic.objects.create(subject=self.subject, name="No History")
        response = self.client.post(reverse("delete_topic", kwargs={"pk": topic.id}))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Topic.objects.filter(pk=topic.pk).exists())

    def test_delete_topic_with_history_deactivates_record(self):
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text="Study vectors",
            status=StudySession.Status.COMPLETED,
        )
        response = self.client.post(
            reverse("delete_topic", kwargs={"pk": self.topic.id})
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.topic.refresh_from_db()
        self.assertFalse(self.topic.is_active)

    def test_delete_subject_without_history_removes_record(self):
        subject = Subject.objects.create(user=self.user, name="No History")
        Topic.objects.create(subject=subject, name="Empty Topic")
        response = self.client.post(
            reverse("delete_subject", kwargs={"pk": subject.id})
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Subject.objects.filter(pk=subject.pk).exists())

    def test_delete_subject_with_history_deactivates_subject_and_topics(self):
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text="Study vectors",
            status=StudySession.Status.COMPLETED,
        )
        response = self.client.post(
            reverse("delete_subject", kwargs={"pk": self.subject.id})
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.subject.refresh_from_db()
        self.topic.refresh_from_db()
        self.assertFalse(self.subject.is_active)
        self.assertFalse(self.topic.is_active)

    def test_delete_rejects_items_from_other_user(self):
        other_subject = Subject.objects.create(user=self.other_user, name=fake.word())
        other_topic = Topic.objects.create(subject=other_subject, name=fake.word())

        self.client.post(reverse("delete_topic", kwargs={"pk": other_topic.id}))
        self.client.post(reverse("delete_subject", kwargs={"pk": other_subject.id}))

        other_subject.refresh_from_db()
        other_topic.refresh_from_db()
        self.assertTrue(other_subject.is_active)
        self.assertTrue(other_topic.is_active)

    def test_dashboard_does_not_render_inactive_study_types(self):
        inactive_subject = Subject.objects.create(
            user=self.user, name="Inactive Subject", is_active=False
        )
        inactive_topic = Topic.objects.create(
            subject=self.subject, name="Inactive Topic", is_active=False
        )
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, inactive_subject.name)
        self.assertNotContains(response, inactive_topic.name)

    def test_complete_topic_stores_summary_and_hides_from_dashboard(self):
        summary = fake.paragraph()
        response = self.client.post(
            reverse("complete_topic", kwargs={"pk": self.topic.id}),
            {"completion_summary": summary},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.topic.refresh_from_db()
        self.assertIsNotNone(self.topic.completed_at)
        self.assertEqual(self.topic.completion_summary, summary)

        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertNotContains(dashboard_response, self.topic.name)

    def test_complete_topic_requires_summary(self):
        response = self.client.post(
            reverse("complete_topic", kwargs={"pk": self.topic.id}),
            {"completion_summary": "  "},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.topic.refresh_from_db()
        self.assertIsNone(self.topic.completed_at)

    def test_complete_topic_rejects_item_from_other_user(self):
        other_subject = Subject.objects.create(user=self.other_user, name=fake.word())
        other_topic = Topic.objects.create(subject=other_subject, name=fake.word())

        self.client.post(
            reverse("complete_topic", kwargs={"pk": other_topic.id}),
            {"completion_summary": fake.paragraph()},
        )

        other_topic.refresh_from_db()
        self.assertIsNone(other_topic.completed_at)

    def test_complete_topic_rejects_active_session(self):
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text=fake.sentence(),
            status=StudySession.Status.IN_PROGRESS,
        )

        response = self.client.post(
            reverse("complete_topic", kwargs={"pk": self.topic.id}),
            {"completion_summary": fake.paragraph()},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.topic.refresh_from_db()
        self.assertIsNone(self.topic.completed_at)

    def test_complete_subject_stores_summary_and_completes_topics(self):
        second_topic = Topic.objects.create(subject=self.subject, name=fake.word())
        summary = fake.paragraph()

        response = self.client.post(
            reverse("complete_subject", kwargs={"pk": self.subject.id}),
            {"completion_summary": summary},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.subject.refresh_from_db()
        self.topic.refresh_from_db()
        second_topic.refresh_from_db()
        self.assertIsNotNone(self.subject.completed_at)
        self.assertEqual(self.subject.completion_summary, summary)
        self.assertIsNotNone(self.topic.completed_at)
        self.assertIsNotNone(second_topic.completed_at)

    def test_complete_subject_rejects_active_session(self):
        StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text=fake.sentence(),
            status=StudySession.Status.PAUSED,
        )

        response = self.client.post(
            reverse("complete_subject", kwargs={"pk": self.subject.id}),
            {"completion_summary": fake.paragraph()},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.subject.refresh_from_db()
        self.assertIsNone(self.subject.completed_at)

    def test_complete_subject_rejects_item_from_other_user(self):
        other_subject = Subject.objects.create(user=self.other_user, name=fake.word())
        Topic.objects.create(subject=other_subject, name=fake.word())

        self.client.post(
            reverse("complete_subject", kwargs={"pk": other_subject.id}),
            {"completion_summary": fake.paragraph()},
        )

        other_subject.refresh_from_db()
        self.assertIsNone(other_subject.completed_at)

    def test_completed_studies_page_lists_summaries_and_sessions(self):
        session = StudySession.objects.create(
            user=self.user,
            topic=self.topic,
            objective_text="Study FastAPI routing",
            objective_result="Routes finished.",
            learning_note="Dependencies are clearer now.",
            status=StudySession.Status.COMPLETED,
            end_time=timezone.now(),
        )
        self.topic.completed_at = timezone.now()
        self.topic.completion_summary = "Topic finished with routing notes."
        self.topic.save(update_fields=["completed_at", "completion_summary"])

        response = self.client.get(reverse("completed_studies"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.topic.name)
        self.assertContains(response, self.topic.completion_summary)
        self.assertContains(response, session.objective_text)
        self.assertContains(response, session.learning_note)

    def test_start_session_rejects_completed_topic(self):
        self.topic.completed_at = timezone.now()
        self.topic.completion_summary = fake.paragraph()
        self.topic.save(update_fields=["completed_at", "completion_summary"])

        response = self.client.post(
            reverse("start_session"),
            {"topic_id": self.topic.id, "objective_text": fake.sentence()},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudySession.objects.count(), 0)
