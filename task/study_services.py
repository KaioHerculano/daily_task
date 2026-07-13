from django.utils import timezone

from .exceptions import (
    ActiveSessionExistsError,
    InvalidStateTransitionError,
    SessionNotActiveError,
)
from .models import SessionPause, StudySession, Topic


def start_session(user, topic_id, objective_text="", mode=StudySession.Mode.FREE):
    active_session = StudySession.objects.filter(
        user=user,
        status__in=[StudySession.Status.IN_PROGRESS, StudySession.Status.PAUSED],
    ).first()
    if active_session:
        raise ActiveSessionExistsError("User already has an active or paused session.")

    topic = Topic.objects.get(id=topic_id)
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


def stop_session(user):
    session = StudySession.objects.filter(
        user=user,
        status__in=[StudySession.Status.IN_PROGRESS, StudySession.Status.PAUSED],
    ).first()

    if not session:
        raise SessionNotActiveError("No active session found.")

    if session.status == StudySession.Status.PAUSED:
        active_pause = session.pauses.filter(pause_end__isnull=True).first()
        if active_pause:
            active_pause.pause_end = timezone.now()
            active_pause.save()

    session.status = StudySession.Status.COMPLETED
    session.end_time = timezone.now()
    session.save()
    return session
