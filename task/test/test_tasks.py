from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from faker import Faker

from accounts.models import UserProfile
from task.models import DailyReminderLog, Subject, TaskDay, Topic, WeeklyPlan
from task.services import get_streak_data, get_weekly_goal_data
from task.tasks import (
    generate_weekly_plans,
    send_daily_reminders,
    send_weekly_plan_email,
)

fake = Faker()


class DailyReminderTaskTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.today = timezone.localdate()

    def test_streak_calculation(self):
        TaskDay.objects.create(user=self.user, date=self.today)
        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=1))
        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=2))
        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=4))
        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=5))
        data = get_streak_data(self.user)
        self.assertEqual(data["current_streak"], 3)
        self.assertEqual(data["best_streak"], 3)

    def test_weekly_goal_calculation(self):
        self.user.profile.weekly_goal = 4
        self.user.profile.save()
        start_of_week = self.today - timedelta(days=self.today.weekday())
        TaskDay.objects.create(user=self.user, date=start_of_week)
        TaskDay.objects.create(user=self.user, date=start_of_week + timedelta(days=1))
        data = get_weekly_goal_data(self.user)
        self.assertEqual(data["weekly_goal"], 4)
        self.assertEqual(data["days_studied_this_week"], 2)
        self.assertEqual(data["goal_percentage"], 50)

    @patch("task.tasks.process_user_reminder.delay")
    def test_send_daily_reminders_prevents_duplicates(self, mock_process_reminder):
        user2 = User.objects.create_user(username=fake.user_name(), email=fake.email())
        TaskDay.objects.create(user=user2, date=self.today)
        processed_count = send_daily_reminders()
        self.assertEqual(processed_count, 1)
        self.assertEqual(mock_process_reminder.call_count, 1)
        DailyReminderLog.objects.create(user=self.user, date=self.today)
        mock_process_reminder.reset_mock()
        processed_count_2 = send_daily_reminders()
        self.assertEqual(processed_count_2, 0)
        self.assertEqual(mock_process_reminder.call_count, 0)


class WeeklyPlanTaskTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name="Software")
        self.topic = Topic.objects.create(subject=self.subject, name="Architecture")

    @patch("task.tasks.send_weekly_plan_email.delay")
    @patch("task.ai_services.generate_weekly_plan_with_ai")
    def test_generate_weekly_plans_processes_active_users(
        self, mock_generate, mock_send_email
    ):
        mock_generate.return_value = object()

        inactive_user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )

        count = generate_weekly_plans()

        self.assertEqual(count, 1)
        mock_generate.assert_called_once_with(
            self.user, week_start=None, force_refresh=False
        )
        mock_send_email.assert_called_once_with(
            self.user.id, plan_id=None, status="success"
        )

    @patch("task.tasks.send_weekly_plan_email.delay")
    @patch("task.ai_services.generate_weekly_plan_with_ai")
    def test_generate_weekly_plans_resilient_to_individual_failure(
        self, mock_generate, mock_send_email
    ):
        user2 = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        subject2 = Subject.objects.create(user=user2, name="Math")
        Topic.objects.create(subject=subject2, name="Algebra")

        mock_generate.side_effect = [RuntimeError("AI failure"), object()]

        count = generate_weekly_plans()

        self.assertEqual(count, 1)
        self.assertEqual(mock_generate.call_count, 2)
        self.assertEqual(mock_send_email.call_count, 2)
        mock_send_email.assert_any_call(self.user.id, plan_id=None, status="failure")
        mock_send_email.assert_any_call(user2.id, plan_id=None, status="success")

    def test_send_weekly_plan_email_success(self):
        today = timezone.localdate()
        plan = WeeklyPlan.objects.create(
            user=self.user,
            week_start=today,
            week_end=today + timedelta(days=6),
        )
        send_weekly_plan_email(self.user.id, plan_id=plan.id, status="success")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertEqual(email.subject, "Seu plano de estudos semanal está pronto!")
        self.assertIn("Seu plano estratégico de estudos para esta semana foi gerado", email.body)
        self.assertEqual(len(email.alternatives), 1)
        self.assertIn("Acessar Meu Plano Semanal", email.alternatives[0][0])

    def test_send_weekly_plan_email_failure(self):
        send_weekly_plan_email(self.user.id, plan_id=None, status="failure")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertEqual(
            email.subject, "Aviso: Não foi possível gerar seu plano semanal de estudos"
        )
        self.assertIn("Não foi possível gerar automaticamente", email.body)
        self.assertEqual(len(email.alternatives), 1)
        self.assertIn("Acessar Daily Task", email.alternatives[0][0])

    def test_send_weekly_plan_email_nonexistent_user(self):
        send_weekly_plan_email(999999, plan_id=None, status="success")
        self.assertEqual(len(mail.outbox), 0)

    def test_send_weekly_plan_email_user_without_email(self):
        user_no_email = User.objects.create_user(
            username=fake.user_name(), email="", password=fake.password()
        )
        send_weekly_plan_email(user_no_email.id, plan_id=None, status="success")
        self.assertEqual(len(mail.outbox), 0)

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_send_weekly_plan_email_raises_on_mail_error(self, mock_send):
        mock_send.side_effect = RuntimeError("SMTP connection failed")
        with self.assertRaises(RuntimeError):
            send_weekly_plan_email(self.user.id, plan_id=None, status="success")


