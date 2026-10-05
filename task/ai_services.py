from dataclasses import dataclass
from datetime import date, timedelta
import json

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


@dataclass(frozen=True)
class PlannerContext:
    user: User
    week_start: date
    week_end: date
    topics: list
    high_priority_topics: list
    other_topics: list
    weekday_minutes: int
    weekend_minutes: int

    @property
    def has_topics(self):
        return bool(self.topics)

    @property
    def valid_topic_ids(self):
        return {topic.id for topic in self.topics}


def build_planner_context(user, week_start=None):
    if week_start is None:
        resolved_start, resolved_end = get_week_bounds()
    else:
        resolved_start = week_start
        resolved_end = week_start + timedelta(days=6)

    pending_topics = list(get_user_pending_topics(user))
    high_topics = [t for t in pending_topics if t.priority == Topic.Priority.HIGH]
    other_topics = [t for t in pending_topics if t.priority != Topic.Priority.HIGH]

    weekday_minutes = 60
    weekend_minutes = 60
    if hasattr(user, "profile"):
        weekday_minutes = user.profile.daily_study_minutes_weekday
        weekend_minutes = user.profile.daily_study_minutes_weekend

    return PlannerContext(
        user=user,
        week_start=resolved_start,
        week_end=resolved_end,
        topics=pending_topics,
        high_priority_topics=high_topics,
        other_topics=other_topics,
        weekday_minutes=weekday_minutes,
        weekend_minutes=weekend_minutes,
    )


def build_deterministic_weekly_plan(context):
    day_budgets = {
        day: (context.weekday_minutes if day < 5 else context.weekend_minutes)
        for day in range(7)
    }
    available_days = [day for day, budget in day_budgets.items() if budget >= 15]
    if not available_days:
        available_days = list(range(5))
        day_budgets = {day: 60 for day in available_days}

    items = []
    other_index = 0
    total_other = len(context.other_topics)

    for day in available_days:
        budget = day_budgets[day]
        order = 1
        remaining_budget = budget

        if context.high_priority_topics:
            num_high = len(context.high_priority_topics)
            target_high_budget = budget if total_other == 0 else max(30, (budget * 2) // 3)
            high_duration = max(15, target_high_budget // num_high)

            for high_topic in context.high_priority_topics:
                if remaining_budget < 15:
                    break
                session_time = min(high_duration, remaining_budget)
                items.append(
                    {
                        "day_of_week": day,
                        "topic_id": high_topic.id,
                        "duration_minutes": session_time,
                        "order": order,
                    }
                )
                order += 1
                remaining_budget -= session_time

        if total_other > 0 and remaining_budget >= 15:
            topic = context.other_topics[other_index % total_other]
            other_index += 1
            items.append(
                {
                    "day_of_week": day,
                    "topic_id": topic.id,
                    "duration_minutes": remaining_budget,
                    "order": order,
                }
            )

    return items


def can_reuse_previous_plan(user, previous_plan, current_topics):
    if not previous_plan:
        return False
    previous_items = list(previous_plan.items.all())
    if not previous_items:
        return False

    previous_topic_ids = {item.topic_id for item in previous_items}
    current_topic_ids = {t.id for t in current_topics}

    return previous_topic_ids == current_topic_ids


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


def try_reuse_previous_plan(context, force_refresh=False):
    if force_refresh:
        return None
    previous_week_start = context.week_start - timedelta(days=7)
    previous_plan = (
        WeeklyPlan.objects.filter(user=context.user, week_start=previous_week_start)
        .prefetch_related("items")
        .first()
    )
    if can_reuse_previous_plan(context.user, previous_plan, context.topics):
        return replicate_weekly_plan(previous_plan, context.week_start)
    return None


def try_generate_with_ai(context):
    topics_payload = [
        {
            "id": t.id,
            "name": t.name,
            "subject": t.subject.name,
            "priority": t.priority,
        }
        for t in context.topics
    ]
    prompt_content = build_weekly_planner_prompt(
        username=context.user.username,
        topics_payload=topics_payload,
        weekday_minutes=context.weekday_minutes,
        weekend_minutes=context.weekend_minutes,
        week_start=context.week_start,
        week_end=context.week_end,
    )
    try:
        provider = get_ai_provider()
        messages = [
            {"role": "system", "content": WEEKLY_PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ]
        response_json = provider.generate_json(messages)
        return validate_weekly_planner_response(response_json, context.valid_topic_ids)
    except Exception:
        return None


def persist_weekly_plan(context, items_data):
    with transaction.atomic():
        plan, _ = WeeklyPlan.objects.get_or_create(
            user=context.user,
            week_start=context.week_start,
            defaults={"week_end": context.week_end},
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


def generate_weekly_plan_with_ai(user, week_start=None, force_refresh=False):
    context = build_planner_context(user, week_start)
    if not context.has_topics:
        return None

    existing_plan = WeeklyPlan.objects.filter(
        user=user, week_start=context.week_start
    ).first()
    if existing_plan and existing_plan.items.exists() and not force_refresh:
        return existing_plan

    reused_plan = try_reuse_previous_plan(context, force_refresh)
    if reused_plan:
        return reused_plan

    items_data = try_generate_with_ai(context) or build_deterministic_weekly_plan(context)
    return persist_weekly_plan(context, items_data)


