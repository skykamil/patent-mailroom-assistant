class CaseAlreadyExistsError(Exception):
    pass


class CaseNotFoundError(Exception):
    pass


class CaseInUseError(Exception):
    pass


class CaseReferenceNotFoundError(Exception):
    pass


class InvalidEmailError(Exception):
    pass


class InvalidFileSelectionError(Exception):
    pass
