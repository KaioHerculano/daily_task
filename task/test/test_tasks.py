from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from task.models import TaskDay, UserProfile, DailyReminderLog
from task.services import get_streak_data, get_weekly_goal_data
from task.tasks import send_daily_reminders
from unittest.mock import patch
from faker import Faker

fake = Faker()


class DailyReminderTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username=fake.user_name(), email=fake.email(), password=fake.password())
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.today = timezone.localdate()

    def test_streak_calculation(self):
        TaskDay.objects.create(user=self.user, date=self.today)
        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=1))
        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=2))

        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=4))
        TaskDay.objects.create(user=self.user, date=self.today - timedelta(days=5))

        data = get_streak_data(self.user)
        self.assertEqual(data['current_streak'], 3)
        self.assertEqual(data['best_streak'], 3)

    def test_weekly_goal_calculation(self):
        self.profile.weekly_goal = 4
        self.profile.save()

        start_of_week = self.today - timedelta(days=self.today.weekday())
        TaskDay.objects.create(user=self.user, date=start_of_week)
        TaskDay.objects.create(user=self.user, date=start_of_week + timedelta(days=1))

        data = get_weekly_goal_data(self.user)
        self.assertEqual(data['weekly_goal'], 4)
        self.assertEqual(data['days_studied_this_week'], 2)
        self.assertEqual(data['goal_percentage'], 50)

    @patch('task.tasks.process_user_reminder.delay')
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