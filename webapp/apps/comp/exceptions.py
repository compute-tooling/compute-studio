import json


class CSException(Exception):
    pass


class CSError(CSException):
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


class ResourceLimitException(CSException):
    collaborators_msg = (
        "You have reached the limit for the number of collaborators "
        "that you can add to this simulation. You may make this "
        "simulation public or upgrade to Compute Studio Pro to "
        "increase the number of collaborators that are allowed on "
        "this plan."
    )

    def __init__(self, resource, *args, **kwargs):
        self.resource = resource
        super().__init__(*args, **kwargs)
