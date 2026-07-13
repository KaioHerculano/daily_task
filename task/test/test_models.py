from datetime import timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from task.models import Subject, Topic, StudySession, SessionPause

class StudyDomainModelsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.subject = Subject.objects.create(user=self.user, name='Math')
        self.topic = Topic.objects.create(subject=self.subject, name='Algebra')

    def test_session_time_properties_without_pauses(self):
        start_time = timezone.now() - timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        session = StudySession.objects.create(user=self.user, topic=self.topic, start_time=start_time, end_time=end_time)
        self.assertEqual(session.gross_time.total_seconds(), 3600)
        self.assertEqual(session.paused_time.total_seconds(), 0)
        self.assertEqual(session.net_time.total_seconds(), 3600)

    def test_session_time_properties_with_pauses(self):
        start_time = timezone.now() - timedelta(hours=2)
        end_time = start_time + timedelta(hours=2)
        session = StudySession.objects.create(user=self.user, topic=self.topic, start_time=start_time, end_time=end_time)
        SessionPause.objects.create(session=session, pause_start=start_time + timedelta(minutes=30), pause_end=start_time + timedelta(minutes=45))
        SessionPause.objects.create(session=session, pause_start=start_time + timedelta(minutes=90), pause_end=start_time + timedelta(minutes=95))
        self.assertEqual(session.gross_time.total_seconds(), 7200)
        self.assertEqual(session.paused_time.total_seconds(), 1200)
        self.assertEqual(session.net_time.total_seconds(), 6000)

    def test_gross_time_when_session_in_progress(self):
        start_time = timezone.now() - timedelta(minutes=30)
        session = StudySession.objects.create(user=self.user, topic=self.topic, start_time=start_time, status=StudySession.Status.IN_PROGRESS)
        gross = session.gross_time.total_seconds()
        self.assertGreaterEqual(gross, 1800)
        self.assertLess(gross, 1805)
