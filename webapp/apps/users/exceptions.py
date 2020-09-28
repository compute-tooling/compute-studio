from webapp.apps.exceptions import CSException


class ResourceLimitException(CSException):
    collaborators_msg = (
        "You have reached the limit for the number of collaborators "
        "on private apps. You may make this app public "
        "or upgrade to Compute Studio Plus or Pro to add more "
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
