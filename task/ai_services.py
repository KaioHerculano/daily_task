import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from .ai_providers import get_ai_provider
from .models import StudyInsight, StudySession


def get_week_bounds(reference_date=None):
    today = reference_date or timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def build_weekly_study_payload(user, week_start, week_end):
    sessions = (
        StudySession.objects.filter(
            user=user,
            start_time__date__gte=week_start,
            start_time__date__lte=week_end,
            status=StudySession.Status.COMPLETED,
            end_time__isnull=False,
        )
        .select_related("topic", "topic__subject")
        .prefetch_related("pauses")
        .order_by("start_time")
    )
    return [
        {
            "subject": session.topic.subject.name,
            "topic": session.topic.name,
            "date": session.start_time.date().isoformat(),
            "net_minutes": round(session.net_time.total_seconds() / 60),
            "objective": session.objective_text,
            "objective_achieved": session.objective_achieved,
            "objective_result": session.objective_result,
            "learning_note": session.learning_note,
            "next_step": session.next_step,
        }
        for session in sessions
    ]


def build_insight_prompt(user, payload, week_start, week_end):
    return json.dumps(
        {
            "role": "study_mentor",
            "language": "pt-BR",
            "student": user.username,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "sessions": payload,
            "response_schema": {
                "summary": "string",
                "strengths": "string",
                "risks": "string",
                "next_actions": "string",
            },
        },
        ensure_ascii=False,
    )


def generate_insight_json(prompt):
    return get_ai_provider().generate_json(
        [
            {
                "role": "system",
                "content": "Responda apenas com JSON válido no schema solicitado.",
            },
            {"role": "user", "content": prompt},
        ]
    )


def generate_weekly_insight_for_user(user, reference_date=None):
    week_start, week_end = get_week_bounds(reference_date)
    payload = build_weekly_study_payload(user, week_start, week_end)
    prompt = build_insight_prompt(user, payload, week_start, week_end)
    insight_data = generate_insight_json(prompt)
    insight, _ = StudyInsight.objects.update_or_create(
        user=user,
        week_start=week_start,
        week_end=week_end,
        defaults={
            "summary": insight_data.get("summary", ""),
            "strengths": insight_data.get("strengths", ""),
            "risks": insight_data.get("risks", ""),
            "next_actions": insight_data.get("next_actions", ""),
        },
    )
    return insight


def generate_weekly_insights(reference_date=None):
    week_start, week_end = get_week_bounds(reference_date)
    users = User.objects.filter(
        study_sessions__start_time__date__gte=week_start,
        study_sessions__start_time__date__lte=week_end,
        study_sessions__status=StudySession.Status.COMPLETED,
        study_sessions__end_time__isnull=False,
    ).distinct()
    return [generate_weekly_insight_for_user(user, reference_date) for user in users]
