import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from . import services
from .exceptions import TimerPersistenceError
from .forms import TaskDayForm
from .study_services import pause_session, resume_session, start_session, stop_session


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(services.get_weekly_chart_data(user))
        context.update(services.get_calendar_data(user, self.request))
        context.update(services.get_monthly_chart_data(user, self.request))
        context.update(services.get_streak_data(user))
        context.update(services.get_weekly_goal_data(user))
        context["today"] = timezone.localdate().isoformat()
        context["form"] = TaskDayForm()
        return context

    def post(self, request, *args, **kwargs):
        form = TaskDayForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Dia marcado com sucesso!")
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect("dashboard")


class StartSessionView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            topic_id = data.get("topic_id")
            objective_text = data.get("objective_text", "")
            if not topic_id:
                return JsonResponse({"error": "topic_id is required"}, status=400)
            session = start_session(request.user, topic_id, objective_text)
            return JsonResponse({"status": "started", "session_id": session.id})
        except TimerPersistenceError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class PauseSessionView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            session = pause_session(request.user)
            return JsonResponse({"status": "paused", "session_id": session.id})
        except TimerPersistenceError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class ResumeSessionView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            session = resume_session(request.user)
            return JsonResponse({"status": "resumed", "session_id": session.id})
        except TimerPersistenceError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class StopSessionView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            session = stop_session(request.user)
            return JsonResponse({"status": "stopped", "session_id": session.id})
        except TimerPersistenceError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
