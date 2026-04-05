# app/forms.py

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
