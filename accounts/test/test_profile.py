from django.contrib.auth.models import User
from django.test import TestCase
from faker import Faker

from accounts.services import update_user_profile

fake = Faker()


class UserProfileTest(TestCase):
    def test_profile_created_on_user_creation(self):
        username = fake.user_name()
        user = User.objects.create(username=username, password=fake.password())
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.timezone, "UTC")
        self.assertEqual(user.profile.weekly_goal_hours, 10)
        self.assertEqual(user.profile.preferred_study_time, "MORNING")

    def test_update_user_profile_service(self):
        user = User.objects.create(username=fake.user_name(), password=fake.password())
        data = {
            "timezone": fake.timezone(),
            "weekly_goal_hours": fake.random_int(min=1, max=100),
            "preferred_study_time": fake.random_element(
                elements=("MORNING", "EVENING", "NIGHT")
            ),
            "weekly_goal": fake.random_int(min=1, max=7),
        }

        updated_profile = update_user_profile(user, data)

        self.assertEqual(updated_profile.timezone, data["timezone"])
        self.assertEqual(updated_profile.weekly_goal_hours, data["weekly_goal_hours"])
        self.assertEqual(
            updated_profile.preferred_study_time, data["preferred_study_time"]
        )
        self.assertEqual(updated_profile.weekly_goal, data["weekly_goal"])

        user.profile.refresh_from_db()
        self.assertEqual(user.profile.timezone, data["timezone"])
        self.assertEqual(user.profile.weekly_goal_hours, data["weekly_goal_hours"])
        self.assertEqual(
            user.profile.preferred_study_time, data["preferred_study_time"]
        )
        self.assertEqual(user.profile.weekly_goal, data["weekly_goal"])
