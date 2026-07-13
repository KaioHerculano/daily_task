from datetime import datetime, time, timedelta

from django.db import migrations
from django.utils import timezone


def migrate_taskday_to_studysession(apps, schema_editor):
    TaskDay = apps.get_model("task", "TaskDay")
    Subject = apps.get_model("task", "Subject")
    Topic = apps.get_model("task", "Topic")
    StudySession = apps.get_model("task", "StudySession")

    for task_day in TaskDay.objects.all():
        subject, _ = Subject.objects.get_or_create(
            user=task_day.user, name="Migração Legada"
        )
        topic, _ = Topic.objects.get_or_create(subject=subject, name="Geral")
        start_time = timezone.make_aware(datetime.combine(task_day.date, time(12, 0)))
        end_time = start_time + timedelta(hours=1)
        StudySession.objects.create(
            user=task_day.user,
            topic=topic,
            objective_text="Migração Legada",
            objective_achieved="PENDING",
            mode="FREE",
            status="COMPLETED",
            start_time=start_time,
            end_time=end_time,
        )


def reverse_taskday_migration(apps, schema_editor):
    StudySession = apps.get_model("task", "StudySession")
    Topic = apps.get_model("task", "Topic")
    Subject = apps.get_model("task", "Subject")

    StudySession.objects.filter(
        topic__name="Geral",
        topic__subject__name="Migração Legada",
        objective_text="Migração Legada",
    ).delete()

    for topic in Topic.objects.filter(name="Geral", subject__name="Migração Legada"):
        if not topic.sessions.exists():
            topic.delete()

    for subject in Subject.objects.filter(name="Migração Legada"):
        if not subject.topics.exists():
            subject.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("task", "0005_studysession_sessionpause_subject_topic_and_more"),
    ]

    operations = [
        migrations.RunPython(
            migrate_taskday_to_studysession, reverse_taskday_migration
        ),
    ]
