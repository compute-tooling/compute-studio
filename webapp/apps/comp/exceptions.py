import json


class CSError(Exception):
    pass


class AppError(CSError):
    def __init__(self, parameters, traceback):
        self.parameters = json.dumps(parameters, indent=4)
        self.traceback = traceback
        super().__init__(traceback)


class ValidationError(CSError):
    pass


class BadPostException(CSError):
    def __init__(self, errors, *args, **kwargs):
        self.errors = errors
        super().__init__(*args, **kwargs)


class ForkObjectException(CSError):
    pass


class VersionMismatchException(CSError):
    pass


class PermissionExpiredException(CSError):
    pass
