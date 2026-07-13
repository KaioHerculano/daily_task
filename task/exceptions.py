class TimerPersistenceError(Exception):
    pass


class ActiveSessionExistsError(TimerPersistenceError):
    pass


class SessionNotActiveError(TimerPersistenceError):
    pass


class InvalidStateTransitionError(TimerPersistenceError):
    pass
