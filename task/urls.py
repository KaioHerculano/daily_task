from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("session/start/", views.StartSessionView.as_view(), name="start_session"),
    path("session/pause/", views.PauseSessionView.as_view(), name="pause_session"),
    path("session/resume/", views.ResumeSessionView.as_view(), name="resume_session"),
    path("session/stop/", views.StopSessionView.as_view(), name="stop_session"),
    path("session/widget/", views.TimerWidgetView.as_view(), name="timer_widget"),
    path("subject/create/", views.SubjectCreateView.as_view(), name="create_subject"),
    path(
        "subject/<int:pk>/delete/",
        views.SubjectDeleteView.as_view(),
        name="delete_subject",
    ),
    path("topic/create/", views.TopicCreateView.as_view(), name="create_topic"),
    path(
        "topic/<int:pk>/delete/",
        views.TopicDeleteView.as_view(),
        name="delete_topic",
    ),
]
