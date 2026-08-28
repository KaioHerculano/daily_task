from django.contrib import admin

from .models import (
    DailyReminderLog,
    SessionPause,
    StudyInsight,
    StudySession,
    Subject,
    TaskDay,
    Topic,
)

admin.site.register(StudySession)
admin.site.register(Subject)
admin.site.register(Topic)
admin.site.register(TaskDay)
admin.site.register(DailyReminderLog)
admin.site.register(StudyInsight)
admin.site.register(SessionPause)
