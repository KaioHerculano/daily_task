# task/services.py

from calendar import month_abbr, monthrange
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from .models import TaskDay


def get_streak_data(user):
    """Calcula a ofensiva (streak) atual e a maior já alcançada."""
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
    elif (check_date - timedelta(days=1)) in date_set:
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
    """Calcula o progresso da meta semanal."""
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

    percentage = min(int((days_studied / goal) * 100), 100) if goal > 0 else 0

    return {
        "weekly_goal": goal,
        "days_studied_this_week": days_studied,
        "goal_percentage": percentage,
    }


def get_weekly_chart_data(user):
    """Prepara os dados para o gráfico de frequência semanal."""
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


def get_calendar_data(user, request):
    """Prepara os dados para o calendário do mês selecionado."""
    today = date.today()
    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))

    _, last_day = monthrange(year, month)
    days_in_month = [date(year, month, day) for day in range(1, last_day + 1)]

    studied_days = set(
        TaskDay.objects.filter(
            user=user, date__year=year, date__month=month
        ).values_list("date", flat=True)
    )

    return {
        "calendar_days": [
            {"day": d, "studied": d in studied_days} for d in days_in_month
        ],
        "selected_month": month,
        "selected_year": year,
        "total_studied": len(studied_days),
        "total_days": len(days_in_month),
        "years": list(range(today.year - 5, today.year + 2)),
        "months": list(range(1, 13)),
    }


def get_monthly_chart_data(user, request):
    """Prepara os dados para o gráfico de estudos por mês."""
    today = date.today()
    start_year = int(request.GET.get("start_year", today.year))
    end_year = int(request.GET.get("end_year", today.year))

    if start_year > end_year:
        start_year, end_year = end_year, start_year

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
