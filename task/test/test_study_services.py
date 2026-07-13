from django.contrib.auth.models import User
from django.test import TestCase
from faker import Faker

from task.exceptions import (
    ActiveSessionExistsError,
    InvalidStateTransitionError,
    InvalidTopicError,
    JournalValidationError,
    SessionNotActiveError,
)
from task.models import StudySession, Subject, Topic
from task.study_services import (
    pause_session,
    resume_session,
    start_session,
    stop_session,
)

fake = Faker()


class StudyServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name=fake.word())
        self.topic = Topic.objects.create(subject=self.subject, name=fake.word())

    def test_start_session(self):
        session = start_session(self.user, self.topic.id, "Test Objective")
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.topic, self.topic)
        self.assertEqual(session.status, StudySession.Status.IN_PROGRESS)

    def test_start_session_fails_if_active(self):
        start_session(self.user, self.topic.id, "Test Objective")
        with self.assertRaises(ActiveSessionExistsError):
            start_session(self.user, self.topic.id, "Another Objective")

    def test_start_session_fails_without_objective(self):
        with self.assertRaises(JournalValidationError):
            start_session(self.user, self.topic.id)

    def test_start_session_fails_for_topic_from_another_user(self):
        other_user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        other_subject = Subject.objects.create(user=other_user, name=fake.word())
        other_topic = Topic.objects.create(subject=other_subject, name=fake.word())
        with self.assertRaises(InvalidTopicError):
            start_session(self.user, other_topic.id, "Test Objective")

    def test_pause_session(self):
        session = start_session(self.user, self.topic.id, "Test Objective")
        paused_session = pause_session(self.user)
        self.assertEqual(paused_session.id, session.id)
        self.assertEqual(paused_session.status, StudySession.Status.PAUSED)
        self.assertEqual(paused_session.pauses.count(), 1)
        self.assertIsNotNone(paused_session.pauses.first().pause_start)
        self.assertIsNone(paused_session.pauses.first().pause_end)

    def test_pause_session_fails_if_not_active(self):
        with self.assertRaises(SessionNotActiveError):
            pause_session(self.user)

    def test_pause_session_fails_if_already_paused(self):
        start_session(self.user, self.topic.id, "Test Objective")
        pause_session(self.user)
        with self.assertRaises(InvalidStateTransitionError):
            pause_session(self.user)

    def test_resume_session(self):
        session = start_session(self.user, self.topic.id, "Test Objective")
        pause_session(self.user)
        resumed_session = resume_session(self.user)
        self.assertEqual(resumed_session.id, session.id)
        self.assertEqual(resumed_session.status, StudySession.Status.IN_PROGRESS)
        self.assertIsNotNone(resumed_session.pauses.first().pause_end)

    def test_resume_session_fails_if_not_active(self):
        with self.assertRaises(SessionNotActiveError):
            resume_session(self.user)

    def test_resume_session_fails_if_already_in_progress(self):
        start_session(self.user, self.topic.id, "Test Objective")
        with self.assertRaises(InvalidStateTransitionError):
            resume_session(self.user)

    def test_stop_session_in_progress(self):
        session = start_session(self.user, self.topic.id, "Test Objective")
        stopped_session = stop_session(
            self.user,
            objective_achieved=StudySession.ObjectiveAchieved.YES,
            objective_result="Finished the planned chapter.",
            learning_note="Indexes were the hardest part.",
            next_step="Practice exercises.",
        )
        self.assertEqual(stopped_session.id, session.id)
        self.assertEqual(stopped_session.status, StudySession.Status.COMPLETED)
        self.assertIsNotNone(stopped_session.end_time)
        self.assertEqual(stopped_session.objective_achieved, "YES")
        self.assertEqual(
            stopped_session.objective_result, "Finished the planned chapter."
        )
        self.assertEqual(
            stopped_session.learning_note, "Indexes were the hardest part."
        )
        self.assertEqual(stopped_session.next_step, "Practice exercises.")

    def test_stop_session_when_paused(self):
        session = start_session(self.user, self.topic.id, "Test Objective")
        pause_session(self.user)
        stopped_session = stop_session(
            self.user,
            objective_achieved=StudySession.ObjectiveAchieved.PARTIAL,
            objective_result="Covered the first half.",
            learning_note="Need to review definitions.",
        )
        self.assertEqual(stopped_session.id, session.id)
        self.assertEqual(stopped_session.status, StudySession.Status.COMPLETED)
        self.assertIsNotNone(stopped_session.end_time)
        self.assertIsNotNone(stopped_session.pauses.first().pause_end)

    def test_stop_session_fails_if_not_active(self):
        with self.assertRaises(SessionNotActiveError):
            stop_session(
                self.user,
                objective_achieved=StudySession.ObjectiveAchieved.YES,
                objective_result="Done.",
                learning_note="Clear.",
            )

    def test_stop_session_fails_without_journal(self):
        session = start_session(self.user, self.topic.id, "Test Objective")
        with self.assertRaises(JournalValidationError):
            stop_session(self.user)
        session.refresh_from_db()
        self.assertEqual(session.status, StudySession.Status.IN_PROGRESS)
        self.assertIsNone(session.end_time)
