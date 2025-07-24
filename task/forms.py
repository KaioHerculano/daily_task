# task/forms.py

from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import TaskDay

class TaskDayForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance

    def clean_date(self):
        selected_date = self.cleaned_data.get('date')
        if selected_date and selected_date < date.today():
            raise ValidationError("Você não pode marcar um dia de estudo em uma data que já passou.", code='past_date')
        return selected_date

    def clean(self):
        cleaned_data = super().clean()
        selected_date = cleaned_data.get("date")
        
        if selected_date and self.user:
            if TaskDay.objects.filter(user=self.user, date=selected_date).exists():
                raise ValidationError(
                    "Este dia já foi marcado como um dia de estudo.",
                    code='duplicate_day'
                )
        return cleaned_data


    class Meta:
        model = TaskDay
        fields = ['date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }