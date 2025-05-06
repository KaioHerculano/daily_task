# tracker/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TaskDay
from datetime import date, timedelta

@login_required
def dashboard(request):
    if request.method == 'POST':
        try:
            selected_date = request.POST.get('date')
            TaskDay.objects.create(user=request.user, date=selected_date)
            messages.success(request, 'Dia marcado com sucesso!')
        except:
            messages.error(request, 'Erro: Data já marcada ou inválida!')
    
    task_days = TaskDay.objects.filter(user=request.user).order_by('date')

    today = date.today()

    weekly_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    weekly_data = {day.date: True for day in task_days.filter(date__gte=weekly_dates[0])}
    
    context = {
        'weekly_labels': [d.strftime('%d/%m') for d in weekly_dates],
        'weekly_values': [1 if d in weekly_data else 0 for d in weekly_dates],
        'today': today.isoformat()
    }
    return render(request, 'home.html', context)