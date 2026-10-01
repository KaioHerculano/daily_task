from django.contrib import admin

from .models import (
    DailyReminderLog,
    SessionPause,
    StudyInsight,
    StudySession,
    Subject,
    TaskDay,
    Topic,
    WeeklyPlan,
    WeeklyPlanItem,
)

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "priority", "is_active", "completed_at")
    list_filter = ("priority", "is_active", "subject")
    search_fields = ("name", "subject__name")
    list_editable = ("priority",)


class WeeklyPlanItemInline(admin.TabularInline):
    model = WeeklyPlanItem
    extra = 1
    autocomplete_fields = ("topic",)


@admin.register(WeeklyPlan)
class WeeklyPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "week_start", "week_end", "created_at")
    list_filter = ("week_start", "user")
    search_fields = ("user__username",)
    inlines = [WeeklyPlanItemInline]


@admin.register(WeeklyPlanItem)
class WeeklyPlanItemAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "day_of_week",
        "topic",
        "duration_minutes",
        "is_completed",
        "completed_at",
        "order",
    )
    list_filter = ("day_of_week", "is_completed", "plan__week_start")
    search_fields = ("topic__name", "plan__user__username")
    list_editable = ("is_completed", "order")


admin.site.register(StudySession)
admin.site.register(Subject)
admin.site.register(TaskDay)
admin.site.register(DailyReminderLog)
admin.site.register(StudyInsight)
admin.site.register(SessionPause)

