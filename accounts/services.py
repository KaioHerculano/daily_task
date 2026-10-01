from django.contrib.auth.models import User

ALLOWED_PROFILE_FIELDS = {
    "timezone",
    "weekly_goal_hours",
    "daily_study_minutes_weekday",
    "daily_study_minutes_weekend",
    "preferred_study_time",
    "weekly_goal",
}


def update_user_profile(user: User, data: dict):
    profile = user.profile
    for field, value in data.items():
        if field in ALLOWED_PROFILE_FIELDS:
            setattr(profile, field, value)
    profile.save()
    return profile
