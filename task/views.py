from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from datetime import date
from .forms import TaskDayForm
from . import services

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context.update(services.get_weekly_chart_data(user))
        context.update(services.get_calendar_data(user, self.request))
        context.update(services.get_monthly_chart_data(user, self.request))
        
        context['today'] = date.today().isoformat()
        context['form'] = TaskDayForm()
        
        return context

    def post(self, request, *args, **kwargs):
        form = TaskDayForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dia marcado com sucesso!')
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect('dashboard')