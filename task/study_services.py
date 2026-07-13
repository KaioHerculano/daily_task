from django.db import transaction
from django.utils import timezone

from .exceptions import (
    ActiveSessionExistsError,
    InvalidStateTransitionError,
    InvalidTopicError,
    JournalValidationError,
    SessionNotActiveError,
)
from .models import SessionPause, StudySession, Subject, Topic


def start_session(user, topic_id, objective_text="", mode=StudySession.Mode.FREE):
    objective_text = objective_text.strip()
    if not objective_text:
        raise JournalValidationError("Objective is required.")

    active_session = StudySession.objects.filter(
        user=user,
        status__in=[StudySession.Status.IN_PROGRESS, StudySession.Status.PAUSED],
    ).first()
    if active_session:
        raise ActiveSessionExistsError("User already has an active or paused session.")

    try:
        topic = Topic.objects.get(id=topic_id, subject__user=user)
    except Topic.DoesNotExist as exc:
        raise InvalidTopicError("Topic not found.") from exc
    session = StudySession.objects.create(
        user=user,
        topic=topic,
        objective_text=objective_text,
        mode=mode,
        status=StudySession.Status.IN_PROGRESS,
        start_time=timezone.now(),
    )
    return session


def pause_session(user):
    session = StudySession.objects.filter(
        user=user,
        status__in=[StudySession.Status.IN_PROGRESS, StudySession.Status.PAUSED],
    ).first()

    if not session:
        raise SessionNotActiveError("No active session found.")

    if session.status == StudySession.Status.PAUSED:
        raise InvalidStateTransitionError("Session is already paused.")

    session.status = StudySession.Status.PAUSED
    session.save()

    SessionPause.objects.create(
        session=session,
        pause_start=timezone.now(),
    )
    return session


def resume_session(user):
    session = StudySession.objects.filter(
        user=user,
        status__in=[StudySession.Status.IN_PROGRESS, StudySession.Status.PAUSED],
    ).first()

    if not session:
        raise SessionNotActiveError("No active session found.")

    if session.status == StudySession.Status.IN_PROGRESS:
        raise InvalidStateTransitionError("Session is already in progress.")

    active_pause = session.pauses.filter(pause_end__isnull=True).first()
    if active_pause:
        active_pause.pause_end = timezone.now()
        active_pause.save()

    session.status = StudySession.Status.IN_PROGRESS
    session.save()
    return session


def stop_session(
    user,
    objective_achieved=StudySession.ObjectiveAchieved.PENDING,
    objective_result="",
    learning_note="",
    next_step="",
):
    objective_result = objective_result.strip()
    learning_note = learning_note.strip()
    next_step = next_step.strip()
    valid_results = {choice[0] for choice in StudySession.ObjectiveAchieved.choices}
    if objective_achieved not in valid_results:
        raise JournalValidationError("Invalid objective result.")
    if not objective_result:
        raise JournalValidationError("Objective result is required.")
    if not learning_note:
        raise JournalValidationError("Learning note is required.")

    with transaction.atomic():
        session = (
            StudySession.objects.select_for_update()
            .filter(
                user=user,
                status__in=[
                    StudySession.Status.IN_PROGRESS,
                    StudySession.Status.PAUSED,
                ],
            )
            .first()
        )

        if not session:
            raise SessionNotActiveError("No active session found.")

        end_time = timezone.now()
        if session.status == StudySession.Status.PAUSED:
            SessionPause.objects.filter(session=session, pause_end__isnull=True).update(
                pause_end=end_time
            )

        StudySession.objects.filter(pk=session.pk).update(
            status=StudySession.Status.COMPLETED,
            end_time=end_time,
            objective_achieved=objective_achieved,
            objective_result=objective_result,
            learning_note=learning_note,
            next_step=next_step,
        )
        session.status = StudySession.Status.COMPLETED
        session.end_time = end_time
        session.objective_achieved = objective_achieved
        session.objective_result = objective_result
        session.learning_note = learning_note
        session.next_step = next_step
    return session


def delete_topic(user, topic_id):
    topic = Topic.objects.filter(id=topic_id, subject__user=user).first()
    if not topic:
        raise InvalidTopicError("Topic not found.")
    if topic.sessions.exists():
        Topic.objects.filter(pk=topic.pk).update(is_active=False)
        topic.is_active = False
        return topic, "deactivated"
    topic.delete()
    return topic, "deleted"


def delete_subject(user, subject_id):
    subject = Subject.objects.filter(id=subject_id, user=user).first()
    if not subject:
        raise InvalidTopicError("Subject not found.")
    has_history = StudySession.objects.filter(topic__subject=subject).exists()
    if has_history:
        with transaction.atomic():
            Subject.objects.filter(pk=subject.pk).update(is_active=False)
            Topic.objects.filter(subject=subject).update(is_active=False)
        subject.is_active = False
        return subject, "deactivated"
    subject.delete()
    return subject, "deleted"
