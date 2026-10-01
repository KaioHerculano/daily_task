from django.contrib.auth.models import User


def update_user_profile(user: User, data: dict):
    profile = user.profile

    if "timezone" in data:
        profile.timezone = data["timezone"]
    if "weekly_goal_hours" in data:
        profile.weekly_goal_hours = data["weekly_goal_hours"]
    if "daily_study_minutes_weekday" in data:
        profile.daily_study_minutes_weekday = data["daily_study_minutes_weekday"]
    if "daily_study_minutes_weekend" in data:
        profile.daily_study_minutes_weekend = data["daily_study_minutes_weekend"]
    if "preferred_study_time" in data:
        profile.preferred_study_time = data["preferred_study_time"]
    if "weekly_goal" in data:
        profile.weekly_goal = data["weekly_goal"]

    profile.save()
    return profile
