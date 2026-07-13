from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("session/start/", views.StartSessionView.as_view(), name="start_session"),
    path("session/pause/", views.PauseSessionView.as_view(), name="pause_session"),
    path("session/resume/", views.ResumeSessionView.as_view(), name="resume_session"),
    path("session/stop/", views.StopSessionView.as_view(), name="stop_session"),
]
