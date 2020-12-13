from webapp.apps.exceptions import CSException


class PrivateAppException(CSException):
    msg = "You can upgrade to Compute Studio Pro to make this app private."
    resource = "app"

    def __init__(self, *args):
        msg = args[0] if args else self.msg
        super().__init__(msg)

    def todict(self):
        return dict(
            resource=self.resource,
            test_name="make_app_private",
            upgrade_to="pro",
            msg=str(self),
        )
