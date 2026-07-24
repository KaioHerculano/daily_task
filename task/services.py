from calendar import month_abbr, monthrange
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import DurationField, ExpressionWrapper, F, Max, Prefetch, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import SessionPause, StudyInsight, StudySession, Subject, TaskDay, Topic


def format_duration_hours(value):
    total_minutes = int(round(value * 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h{minutes:02d}min"
    if hours:
        return f"{hours}h"
    return f"{minutes}min"


def get_streak_data(user):
    dates = list(
        TaskDay.objects.filter(user=user)
        .order_by("-date")
        .values_list("date", flat=True)
        .distinct()
    )
    if not dates:
        return {"current_streak": 0, "best_streak": 0}
    today = timezone.localdate()
    current_streak = 0
    date_set = set(dates)
    check_date = today
    if check_date in date_set:
        current_streak += 1
        check_date -= timedelta(days=1)
    elif check_date - timedelta(days=1) in date_set:
        check_date -= timedelta(days=1)
        current_streak += 1
        check_date -= timedelta(days=1)
    if current_streak > 0:
        while check_date in date_set:
            current_streak += 1
            check_date -= timedelta(days=1)
    best_streak = 0
    temp_streak = 1
    for i in range(1, len(dates)):
        if (dates[i - 1] - dates[i]).days == 1:
            temp_streak += 1
        else:
            best_streak = max(best_streak, temp_streak)
            temp_streak = 1
    best_streak = max(best_streak, temp_streak)
    return {"current_streak": current_streak, "best_streak": best_streak}


def get_weekly_goal_data(user):
    goal = 5
    if hasattr(user, "profile"):
        goal = user.profile.weekly_goal
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    days_studied = (
        TaskDay.objects.filter(
            user=user, date__gte=start_of_week, date__lte=end_of_week
        )
        .values("date")
        .distinct()
        .count()
    )
    percentage = min(int(days_studied / goal * 100), 100) if goal > 0 else 0
    return {
        "weekly_goal": goal,
        "days_studied_this_week": days_studied,
        "goal_percentage": percentage,
    }


def get_weekly_chart_data(user):
    today = date.today()
    weekly_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    studied_dates = set(
        TaskDay.objects.filter(user=user, date__gte=weekly_dates[0]).values_list(
            "date", flat=True
        )
    )
    return {
        "weekly_labels": [d.strftime("%d/%m") for d in weekly_dates],
        "weekly_values": [1 if d in studied_dates else 0 for d in weekly_dates],
    }


def get_weekly_net_time(user):
    today = timezone.localdate()
    start_date = today - timedelta(days=6)
    gross_duration = ExpressionWrapper(
        F("end_time") - F("start_time"), output_field=DurationField()
    )
    pause_duration = ExpressionWrapper(
        F("pause_end") - F("pause_start"), output_field=DurationField()
    )
    session_rows = (
        StudySession.objects.filter(
            user=user,
            status=StudySession.Status.COMPLETED,
            start_time__date__gte=start_date,
            end_time__isnull=False,
        )
        .annotate(day=TruncDate("start_time"))
        .values("day")
        .annotate(total=Sum(gross_duration))
    )
    pause_rows = (
        SessionPause.objects.filter(
            session__user=user,
            session__status=StudySession.Status.COMPLETED,
            session__start_time__date__gte=start_date,
            pause_end__isnull=False,
        )
        .annotate(day=TruncDate("session__start_time"))
        .values("day")
        .annotate(total=Sum(pause_duration))
    )
    gross_by_day = {row["day"]: row["total"] or timedelta(0) for row in session_rows}
    pauses_by_day = {row["day"]: row["total"] or timedelta(0) for row in pause_rows}
    weekly_dates = [start_date + timedelta(days=i) for i in range(7)]
    values = []
    total_seconds = 0
    for current_date in weekly_dates:
        net_time = gross_by_day.get(current_date, timedelta(0)) - pauses_by_day.get(
            current_date, timedelta(0)
        )
        total_seconds += net_time.total_seconds()
        values.append(round(net_time.total_seconds() / 3600, 2))
    total_hours = total_seconds / 3600
    today_hours = values[-1] if values else 0
    return {
        "weekly_net_time_labels": [d.strftime("%d/%m") for d in weekly_dates],
        "weekly_net_time_values": values,
        "weekly_net_time_total": round(total_hours, 2),
        "weekly_net_time_total_label": format_duration_hours(total_hours),
        "weekly_net_time_today": today_hours,
        "weekly_net_time_today_label": format_duration_hours(today_hours),
    }


def get_delayed_topics(user):
    cutoff = timezone.now() - timedelta(days=7)
    return (
        Topic.objects.filter(
            subject__user=user,
            is_active=True,
            subject__is_active=True,
            completed_at__isnull=True,
            subject__completed_at__isnull=True,
        )
        .annotate(
            last_completed_session=Max(
                "sessions__end_time",
                filter=Q(sessions__status=StudySession.Status.COMPLETED),
            )
        )
        .filter(
            Q(last_completed_session__lt=cutoff)
            | Q(last_completed_session__isnull=True)
        )
        .select_related("subject")
        .order_by("subject__name", "name")[:8]
    )


def get_latest_insight(user):
    return StudyInsight.objects.filter(user=user).first()


def get_active_subjects_with_topics(user):
    active_topics = Topic.objects.filter(is_active=True, completed_at__isnull=True)
    return Subject.objects.filter(
        user=user,
        is_active=True,
        completed_at__isnull=True,
    ).prefetch_related(Prefetch("topics", queryset=active_topics))


def get_active_study_session(user):
    return StudySession.objects.filter(
        user=user,
        status__in=[StudySession.Status.IN_PROGRESS, StudySession.Status.PAUSED],
    ).first()


def get_study_dashboard_context(user, request):
    context = {}
    context.update(get_weekly_chart_data(user))
    context.update(get_calendar_data(user, request))
    context.update(get_monthly_chart_data(user, request))
    context.update(get_streak_data(user))
    context.update(get_weekly_goal_data(user))
    context.update(get_weekly_net_time(user))
    context["delayed_topics"] = get_delayed_topics(user)
    context["latest_insight"] = get_latest_insight(user)
    context["subjects"] = get_active_subjects_with_topics(user)
    context["active_session"] = get_active_study_session(user)
    context["today"] = timezone.localdate().isoformat()
    return context


def get_calendar_data(user, request):
    today = date.today()
    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))
    _, last_day = monthrange(year, month)
    days_in_month = [date(year, month, day) for day in range(1, last_day + 1)]
    leading_blank_days = (days_in_month[0].weekday() + 1) % 7
    studied_days = set(
        TaskDay.objects.filter(
            user=user, date__year=year, date__month=month
        ).values_list("date", flat=True)
    )
    return {
        "calendar_days": [{"day": None, "studied": False}] * leading_blank_days
        + [{"day": d, "studied": d in studied_days} for d in days_in_month],
        "selected_month": month,
        "selected_year": year,
        "total_studied": len(studied_days),
        "total_days": len(days_in_month),
        "years": list(range(today.year - 5, today.year + 2)),
        "months": list(range(1, 13)),
    }


def get_monthly_chart_data(user, request):
    today = date.today()
    start_year = int(request.GET.get("start_year", today.year))
    end_year = int(request.GET.get("end_year", today.year))
    if start_year > end_year:
        start_year, end_year = (end_year, start_year)
    studies = TaskDay.objects.get_monthly_study_counts(user, start_year, end_year)
    studies_dict = {entry["month"]: entry["total"] for entry in studies}
    all_months_in_range = []
    cursor = date(start_year, 1, 1)
    end_date = date(end_year, 12, 1)
    while cursor <= end_date:
        all_months_in_range.append(cursor)
        cursor += relativedelta(months=1)
    return {
        "monthly_labels": [
            f"{month_abbr[d.month]}/{d.year}" for d in all_months_in_range
        ],
        "monthly_values": [studies_dict.get(d, 0) for d in all_months_in_range],
        "start_year": start_year,
        "end_year": end_year,
    }


def get_completed_studies_context(user):
    completed_topics = (
        Topic.objects.filter(
            subject__user=user,
            is_active=True,
            completed_at__isnull=False,
        )
        .select_related("subject")
        .prefetch_related(
            Prefetch(
                "sessions",
                queryset=StudySession.objects.filter(
                    user=user, status=StudySession.Status.COMPLETED
                )
                .prefetch_related("pauses")
                .order_by("-end_time"),
            )
        )
        .order_by("-completed_at", "subject__name", "name")
    )
    completed_subjects = (
        Subject.objects.filter(
            user=user,
            is_active=True,
            completed_at__isnull=False,
        )
        .prefetch_related(
            Prefetch(
                "topics",
                queryset=Topic.objects.filter(is_active=True).order_by("name"),
            )
        )
        .order_by("-completed_at", "name")
    )
    return {
        "completed_topics": completed_topics,
        "completed_subjects": completed_subjects,
    }
