from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from . import services
from .exceptions import TimerPersistenceError
from .forms import SubjectForm, TaskDayForm, TopicForm
from .models import Subject, Topic
from .study_services import (
    delete_subject,
    delete_topic,
    pause_session,
    resume_session,
    start_session,
    stop_session,
)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(services.get_study_dashboard_context(user, self.request))
        context["form"] = TaskDayForm()
        context["subject_form"] = SubjectForm()
        context["topic_form"] = TopicForm(user=user)
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
            topic_id = request.POST.get("topic_id")
            objective_text = request.POST.get("objective_text", "")
            if not topic_id:
                return JsonResponse({"error": "topic_id is required"}, status=400)
            session = start_session(request.user, topic_id, objective_text)
            return JsonResponse({"status": "started", "session_id": session.id})
        except TimerPersistenceError as e:
            return JsonResponse(
                {"error": str(e), "code": e.__class__.__name__}, status=400
            )
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
            session = stop_session(
                request.user,
                objective_achieved=request.POST.get("objective_achieved", "PENDING"),
                objective_result=request.POST.get("objective_result", ""),
                learning_note=request.POST.get("learning_note", ""),
                next_step=request.POST.get("next_step", ""),
            )
            return JsonResponse({"status": "stopped", "session_id": session.id})
        except TimerPersistenceError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class TimerWidgetView(LoginRequiredMixin, TemplateView):
    template_name = "components/_timer_widget.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        session = services.get_active_study_session(self.request.user)
        context["active_session"] = session
        if session:
            context["elapsed_seconds"] = int(session.net_time.total_seconds())
        else:
            context["elapsed_seconds"] = 0
        return context


class SubjectCreateView(LoginRequiredMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = "home.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Matéria criada com sucesso!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erro ao criar matéria. Verifique os dados.")
        return redirect("dashboard")


class TopicCreateView(LoginRequiredMixin, CreateView):
    model = Topic
    form_class = TopicForm
    template_name = "home.html"
    success_url = reverse_lazy("dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.instance.subject.user != self.request.user:
            messages.error(self.request, "Matéria inválida.")
            return redirect("dashboard")
        messages.success(self.request, "Tópico criado com sucesso!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erro ao criar tópico. Verifique os dados.")
        return redirect("dashboard")


class SubjectDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            _, result = delete_subject(request.user, pk)
            if result == "deactivated":
                messages.success(request, "Matéria desativada e histórico preservado.")
            else:
                messages.success(request, "Matéria removida com sucesso.")
        except TimerPersistenceError as e:
            messages.error(request, str(e))
        return redirect("dashboard")


class TopicDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            _, result = delete_topic(request.user, pk)
            if result == "deactivated":
                messages.success(request, "Tópico desativado e histórico preservado.")
            else:
                messages.success(request, "Tópico removido com sucesso.")
        except TimerPersistenceError as e:
            messages.error(request, str(e))
        return redirect("dashboard")
