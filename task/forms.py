# tracker/forms.py
from django import forms
from .models import TaskDay
from datetime import datetime

class TaskDayForm(forms.ModelForm):
    class Meta:
        model = TaskDay
        fields = ['date']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_date(self):
        selected_date = self.cleaned_data['date']
        today = datetime.today().date()

        if TaskDay.objects.filter(user=self.user, date=selected_date).exists():
            raise forms.ValidationError("Essa data já está marcada.")

        if selected_date > today:
            raise forms.ValidationError("Não é possível marcar uma data futura.")

        if selected_date < today:
            raise forms.ValidationError("Não é possível marcar uma data anterior a hoje.")

        return selected_date
