# task/services.py

from datetime import date, timedelta
from calendar import monthrange, month_abbr
from dateutil.relativedelta import relativedelta
from .models import TaskDay

def get_weekly_chart_data(user):
    """Prepara os dados para o gráfico de frequência semanal."""
    today = date.today()
    weekly_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    studied_dates = set(TaskDay.objects.filter(
        user=user, 
        date__gte=weekly_dates[0]
    ).values_list('date', flat=True))

    return {
        'weekly_labels': [d.strftime('%d/%m') for d in weekly_dates],
        'weekly_values': [1 if d in studied_dates else 0 for d in weekly_dates],
    }

def get_calendar_data(user, request):
    """Prepara os dados para o calendário do mês selecionado."""
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    _, last_day = monthrange(year, month)
    days_in_month = [date(year, month, day) for day in range(1, last_day + 1)]

    studied_days = set(TaskDay.objects.filter(
        user=user,
        date__year=year,
        date__month=month
    ).values_list('date', flat=True))

    return {
        'calendar_days': [{'day': d, 'studied': d in studied_days} for d in days_in_month],
        'selected_month': month,
        'selected_year': year,
        'total_studied': len(studied_days),
        'total_days': len(days_in_month),
        'years': list(range(today.year - 5, today.year + 2)),
        'months': list(range(1, 13)),
    }

def get_monthly_chart_data(user, request):
    """Prepara os dados para o gráfico de estudos por mês."""
    today = date.today()
    start_year = int(request.GET.get('start_year', today.year))
    end_year = int(request.GET.get('end_year', today.year))

    if start_year > end_year:
        start_year, end_year = end_year, start_year
    
    studies = TaskDay.objects.get_monthly_study_counts(user, start_year, end_year)
    studies_dict = {entry['month']: entry['total'] for entry in studies}

    all_months_in_range = []
    cursor = date(start_year, 1, 1)
    end_date = date(end_year, 12, 1)
    while cursor <= end_date:
        all_months_in_range.append(cursor)
        cursor += relativedelta(months=1)

    return {
        'monthly_labels': [f"{month_abbr[d.month]}/{d.year}" for d in all_months_in_range],
        'monthly_values': [studies_dict.get(d, 0) for d in all_months_in_range],
        'start_year': start_year,
        'end_year': end_year,
    }