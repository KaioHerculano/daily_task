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
        self.assertEqual(user.profile.daily_study_minutes_weekday, 60)
        self.assertEqual(user.profile.daily_study_minutes_weekend, 60)

    def test_update_user_profile_service(self):
        user = User.objects.create(username=fake.user_name(), password=fake.password())
        data = {
            "timezone": fake.timezone(),
            "weekly_goal_hours": fake.random_int(min=1, max=100),
            "preferred_study_time": fake.random_element(
                elements=("MORNING", "EVENING", "NIGHT")
            ),
            "weekly_goal": fake.random_int(min=1, max=7),
            "daily_study_minutes_weekday": 90,
            "daily_study_minutes_weekend": 120,
            "non_allowed_field": "injected",
        }

        updated_profile = update_user_profile(user, data)

        self.assertEqual(updated_profile.timezone, data["timezone"])
        self.assertEqual(updated_profile.weekly_goal_hours, data["weekly_goal_hours"])
        self.assertEqual(
            updated_profile.preferred_study_time, data["preferred_study_time"]
        )
        self.assertEqual(updated_profile.weekly_goal, data["weekly_goal"])
        self.assertEqual(updated_profile.daily_study_minutes_weekday, 90)
        self.assertEqual(updated_profile.daily_study_minutes_weekend, 120)
        self.assertFalse(hasattr(updated_profile, "non_allowed_field"))

        user.profile.refresh_from_db()
        self.assertEqual(user.profile.timezone, data["timezone"])
        self.assertEqual(user.profile.weekly_goal_hours, data["weekly_goal_hours"])
        self.assertEqual(
            user.profile.preferred_study_time, data["preferred_study_time"]
        )
        self.assertEqual(user.profile.weekly_goal, data["weekly_goal"])
        self.assertEqual(user.profile.daily_study_minutes_weekday, 90)
        self.assertEqual(user.profile.daily_study_minutes_weekend, 120)


from django.urls import reverse
from accounts.forms import UserProfileForm


class ProfileViewAndFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.client.force_login(self.user)

    def test_profile_form_valid(self):
        form = UserProfileForm(
            data={
                "weekly_goal": 5,
                "weekly_goal_hours": 15,
                "daily_study_minutes_weekday": 45,
                "daily_study_minutes_weekend": 90,
                "preferred_study_time": "NIGHT",
                "timezone": "America/Sao_Paulo",
            },
            instance=self.user.profile,
        )
        self.assertTrue(form.is_valid())

    def test_profile_form_invalid_weekday_minutes(self):
        form = UserProfileForm(
            data={
                "weekly_goal": 5,
                "weekly_goal_hours": 15,
                "daily_study_minutes_weekday": 5,
                "daily_study_minutes_weekend": 90,
                "preferred_study_time": "NIGHT",
                "timezone": "America/Sao_Paulo",
            },
            instance=self.user.profile,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("daily_study_minutes_weekday", form.errors)

    def test_profile_view_get(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("profile_form", response.context)
        self.assertContains(response, "Metas e Disponibilidade de Estudo")

    def test_profile_view_post_updates_profile(self):
        response = self.client.post(
            reverse("profile"),
            {
                "username": self.user.username,
                "email": "newemail@example.com",
                "weekly_goal": 6,
                "weekly_goal_hours": 20,
                "daily_study_minutes_weekday": 75,
                "daily_study_minutes_weekend": 150,
                "preferred_study_time": "EVENING",
                "timezone": "UTC",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "newemail@example.com")
        self.assertEqual(self.user.profile.daily_study_minutes_weekday, 75)
        self.assertEqual(self.user.profile.daily_study_minutes_weekend, 150)
        self.assertEqual(self.user.profile.weekly_goal, 6)
