from django import forms
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User
from django.template.loader import render_to_string

from app.tasks import send_email_task


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email"]


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email"]


from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "weekly_goal",
            "weekly_goal_hours",
            "daily_study_minutes_weekday",
            "daily_study_minutes_weekend",
            "preferred_study_time",
            "timezone",
        ]
        labels = {
            "weekly_goal": "Meta Semanal (dias)",
            "weekly_goal_hours": "Meta Semanal (horas totais)",
            "daily_study_minutes_weekday": "Meta Diária - Dias Úteis (minutos)",
            "daily_study_minutes_weekend": "Meta Diária - Fim de Semana (minutos)",
            "preferred_study_time": "Horário Preferido de Estudo",
            "timezone": "Fuso Horário",
        }
        widgets = {
            "weekly_goal": forms.NumberInput(attrs={"class": "form-control"}),
            "weekly_goal_hours": forms.NumberInput(attrs={"class": "form-control"}),
            "daily_study_minutes_weekday": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "daily_study_minutes_weekend": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "preferred_study_time": forms.Select(attrs={"class": "form-select"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
        }


class AsyncPasswordResetForm(PasswordResetForm):

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        html_email = None
        if html_email_template_name is not None:
            html_email = render_to_string(html_email_template_name, context)
        send_email_task.delay(subject, body, from_email, to_email, html_email)
