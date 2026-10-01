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

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "priority", "is_active", "completed_at")
    list_filter = ("priority", "is_active", "subject")
    search_fields = ("name", "subject__name")
    list_editable = ("priority",)


admin.site.register(StudySession)
admin.site.register(Subject)
admin.site.register(TaskDay)
admin.site.register(DailyReminderLog)
admin.site.register(StudyInsight)
admin.site.register(SessionPause)
