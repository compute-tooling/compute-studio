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


class PrivateSimException(CSException):
    msg = (
        "You have reached the limit for the number of private simulations "
        "for this month. You can upgrade to Compute Studio Pro to have an "
        "unlimited number of private simulations."
    )
    resource = "simulation"

    def __init__(self, *args):
        msg = args[0] if args else self.msg
        super().__init__(msg)

    def todict(self):
        return dict(
            resource=self.resource,
            test_name="make_simulation_private",
            upgrade_to="pro",
            msg=str(self),
        )


class PrivateAppException(CSException):
    msg = (
        "This user does not have access to this app. You must grant access"
        "for them to use the app before you can add them as a collaborator."
    )
    resource = "collaborator"

    def __init__(self, collaborator, *args, **kwargs):
        self.collaborator = collaborator
        msg = args[0] if args else self.msg
        super().__init__(msg)

    def todict(self):
        return dict(
            resource=self.resource,
            test_name="add_collaborator_on_private_app",
            collaborator=getattr(self.collaborator, "username", str(self.collaborator)),
            msg=str(self),
        )


class NotReady(CSException):
    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)


class Stale(CSException):
    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
