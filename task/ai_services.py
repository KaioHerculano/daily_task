import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone

from .ai_providers import get_ai_provider
from .models import (
    StudyInsight,
    StudySession,
    Topic,
    WeeklyPlan,
    WeeklyPlanItem,
)
from .prompts.weekly_planner import (
    WEEKLY_PLANNER_SYSTEM_PROMPT,
    build_weekly_planner_prompt,
    validate_weekly_planner_response,
)


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
    system_prompt = (
        "Responda apenas com JSON válido no schema solicitado. "
        "Seja objetivo e analítico, sem floreios. "
        "Não invente problemas nem 'encha linguiça'. "
        "Se não houver problemas, gargalos ou riscos estruturais reais identificados na semana, "
        "você DEVE retornar o campo 'risks' estritamente como uma string vazia ('')."
    )
    return get_ai_provider().generate_json(
        [
            {
                "role": "system",
                "content": system_prompt,
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


def get_user_pending_topics(user):
    return (
        Topic.objects.filter(
            subject__user=user,
            is_active=True,
            subject__is_active=True,
            completed_at__isnull=True,
            subject__completed_at__isnull=True,
        )
        .select_related("subject")
        .order_by(
            models.Case(
                models.When(priority=Topic.Priority.HIGH, then=0),
                models.When(priority=Topic.Priority.MEDIUM, then=1),
                models.When(priority=Topic.Priority.LOW, then=2),
                default=1,
            ),
            "subject__name",
            "name",
        )
    )


def build_deterministic_weekly_plan(topics, weekday_minutes, weekend_minutes):
    day_budgets = {
        day: (weekday_minutes if day < 5 else weekend_minutes)
        for day in range(7)
    }
    available_days = [day for day, budget in day_budgets.items() if budget >= 15]
    if not available_days:
        available_days = list(range(5))
        day_budgets = {day: 60 for day in available_days}

    items = []
    topic_index = 0
    total_topics = len(topics)

    for day in available_days:
        budget = day_budgets[day]
        if budget <= 60:
            session_durations = [budget]
        elif budget <= 120:
            session_durations = [budget // 2, budget - (budget // 2)]
        else:
            session_durations = [60, budget - 60]

        order = 1
        for duration in session_durations:
            if duration < 15:
                continue
            topic = topics[topic_index % total_topics]
            topic_index += 1
            items.append(
                {
                    "day_of_week": day,
                    "topic_id": topic.id,
                    "duration_minutes": duration,
                    "order": order,
                }
            )
            order += 1

    return items


def can_reuse_previous_plan(user, previous_plan, current_topics):
    if not previous_plan:
        return False
    previous_items = list(previous_plan.items.all())
    if not previous_items:
        return False

    previous_topic_ids = {item.topic_id for item in previous_items}
    current_topic_ids = {t.id for t in current_topics}

    if previous_topic_ids != current_topic_ids:
        return False

    return True


def replicate_weekly_plan(previous_plan, new_week_start):
    week_end = new_week_start + timedelta(days=6)
    with transaction.atomic():
        plan, _ = WeeklyPlan.objects.get_or_create(
            user=previous_plan.user,
            week_start=new_week_start,
            defaults={"week_end": week_end},
        )
        plan.items.all().delete()
        new_items = [
            WeeklyPlanItem(
                plan=plan,
                day_of_week=item.day_of_week,
                topic_id=item.topic_id,
                duration_minutes=item.duration_minutes,
                order=item.order,
                is_completed=False,
                completed_at=None,
            )
            for item in previous_plan.items.all()
        ]
        WeeklyPlanItem.objects.bulk_create(new_items)
        return plan


def generate_weekly_plan_with_ai(user, week_start=None, force_refresh=False):
    if week_start is None:
        week_start, week_end = get_week_bounds()
    else:
        week_end = week_start + timedelta(days=6)

    topics = list(get_user_pending_topics(user))
    if not topics:
        return None

    weekday_minutes = 60
    weekend_minutes = 60
    if hasattr(user, "profile"):
        weekday_minutes = user.profile.daily_study_minutes_weekday
        weekend_minutes = user.profile.daily_study_minutes_weekend

    existing_plan = WeeklyPlan.objects.filter(
        user=user, week_start=week_start
    ).first()
    if existing_plan and existing_plan.items.exists() and not force_refresh:
        return existing_plan

    if not force_refresh:
        previous_week_start = week_start - timedelta(days=7)
        previous_plan = (
            WeeklyPlan.objects.filter(user=user, week_start=previous_week_start)
            .prefetch_related("items")
            .first()
        )
        if can_reuse_previous_plan(user, previous_plan, topics):
            return replicate_weekly_plan(previous_plan, week_start)

    topics_payload = [
        {
            "id": t.id,
            "name": t.name,
            "subject": t.subject.name,
            "priority": t.priority,
        }
        for t in topics
    ]
    prompt_content = build_weekly_planner_prompt(
        username=user.username,
        topics_payload=topics_payload,
        weekday_minutes=weekday_minutes,
        weekend_minutes=weekend_minutes,
        week_start=week_start,
        week_end=week_end,
    )
    valid_topic_ids = {t.id for t in topics}

    try:
        provider = get_ai_provider()
        messages = [
            {"role": "system", "content": WEEKLY_PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ]
        response_json = provider.generate_json(messages)
        items_data = validate_weekly_planner_response(
            response_json, valid_topic_ids
        )
    except Exception:
        items_data = build_deterministic_weekly_plan(
            topics, weekday_minutes, weekend_minutes
        )

    with transaction.atomic():
        plan, _ = WeeklyPlan.objects.get_or_create(
            user=user,
            week_start=week_start,
            defaults={"week_end": week_end},
        )
        plan.items.all().delete()
        plan_items = [
            WeeklyPlanItem(
                plan=plan,
                day_of_week=item["day_of_week"],
                topic_id=item["topic_id"],
                duration_minutes=item["duration_minutes"],
                order=item.get("order", 0),
            )
            for item in items_data
        ]
        WeeklyPlanItem.objects.bulk_create(plan_items)
        return plan

