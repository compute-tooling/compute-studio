import json

from webapp.apps.exceptions import CSException, CSError


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
        "on private simulations. You may make this simulation public "
        "or upgrade to Compute Studio Pro to add more "
        "collaborators."
    )

    def __init__(self, resource, test_name, upgrade_to, *args, **kwargs):
        self.resource = resource
        self.upgrade_to = upgrade_to
        self.test_name = test_name
        super().__init__(*args, **kwargs)

    def todict(self):
        return dict(
            resource=self.resource,
            test_name=self.test_name,
            upgrade_to=self.upgrade_to,
            msg=str(self),
        )


class PrivateAppException(CSException):
    collaborators_msg = (
        "This user does not have access to this app. You must grant access"
        "for them to use the app before you can add them as a collaborator."
    )

    def __init__(self, resource, test_name, collaborator, *args, **kwargs):
        self.resource = resource
        self.test_name = test_name
        self.collaborator = collaborator
        super().__init__(*args, **kwargs)

    def todict(self):
        return dict(
            resource=self.resource,
            test_name=self.test_name,
            collaborator=getattr(self.collaborator, "username", str(self.collaborator)),
            msg=str(self),
        )
