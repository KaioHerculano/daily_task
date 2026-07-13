from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from .forms import UserProfileForm, UserRegisterForm, UserUpdateForm
from .services import update_user_profile


class RegisterView(View):

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")
        form = UserRegisterForm()
        return render(request, "registration/register.html", {"form": form})

    def post(self, request):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Bem-vindo, {user.username}! Sua conta foi criada com sucesso.",
            )
            return redirect("dashboard")
        return render(request, "registration/register.html", {"form": form})


class ProfileView(LoginRequiredMixin, View):

    def get(self, request):
        form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)
        return render(
            request, "profile.html", {"form": form, "profile_form": profile_form}
        )

    def post(self, request):
        form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.profile)

        if form.is_valid() and profile_form.is_valid():
            form.save()
            update_user_profile(request.user, profile_form.cleaned_data)
            messages.success(request, "Seu perfil foi atualizado com sucesso!")
            return redirect("profile")

        return render(
            request, "profile.html", {"form": form, "profile_form": profile_form}
        )
