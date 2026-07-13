from django.contrib.auth.models import User
from django.test import TestCase
from faker import Faker

from task.exceptions import (
    ActiveSessionExistsError,
    InvalidStateTransitionError,
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
        start_session(self.user, self.topic.id)
        with self.assertRaises(ActiveSessionExistsError):
            start_session(self.user, self.topic.id)

    def test_pause_session(self):
        session = start_session(self.user, self.topic.id)
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
        start_session(self.user, self.topic.id)
        pause_session(self.user)
        with self.assertRaises(InvalidStateTransitionError):
            pause_session(self.user)

    def test_resume_session(self):
        session = start_session(self.user, self.topic.id)
        pause_session(self.user)
        resumed_session = resume_session(self.user)
        self.assertEqual(resumed_session.id, session.id)
        self.assertEqual(resumed_session.status, StudySession.Status.IN_PROGRESS)
        self.assertIsNotNone(resumed_session.pauses.first().pause_end)

    def test_resume_session_fails_if_not_active(self):
        with self.assertRaises(SessionNotActiveError):
            resume_session(self.user)

    def test_resume_session_fails_if_already_in_progress(self):
        start_session(self.user, self.topic.id)
        with self.assertRaises(InvalidStateTransitionError):
            resume_session(self.user)

    def test_stop_session_in_progress(self):
        session = start_session(self.user, self.topic.id)
        stopped_session = stop_session(self.user)
        self.assertEqual(stopped_session.id, session.id)
        self.assertEqual(stopped_session.status, StudySession.Status.COMPLETED)
        self.assertIsNotNone(stopped_session.end_time)

    def test_stop_session_when_paused(self):
        session = start_session(self.user, self.topic.id)
        pause_session(self.user)
        stopped_session = stop_session(self.user)
        self.assertEqual(stopped_session.id, session.id)
        self.assertEqual(stopped_session.status, StudySession.Status.COMPLETED)
        self.assertIsNotNone(stopped_session.end_time)
        self.assertIsNotNone(stopped_session.pauses.first().pause_end)

    def test_stop_session_fails_if_not_active(self):
        with self.assertRaises(SessionNotActiveError):
            stop_session(self.user)
