class ApplicationNumberAlreadyExistsError(Exception):
    pass


class CaseAlreadyExistsError(Exception):
    pass


class CaseNotFoundError(Exception):
    pass


class CaseInUseError(Exception):
    pass


class InvalidEmailError(Exception):
    pass


class CorrespondenceNotFoundError(Exception):
    pass


class AnalysisNotFoundError(Exception):
    pass


class AnalysisAlreadyApprovedError(Exception):
    pass


class EventNotFoundError(Exception):
    pass


class EventCaseMismatchError(Exception):
    pass


class EventTypeMismatchError(Exception):
    pass
