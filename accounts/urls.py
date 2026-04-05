from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import AsyncPasswordResetForm

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            form_class=AsyncPasswordResetForm,
            html_email_template_name="registration/password_reset_email_html.html",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
