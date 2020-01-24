from rest_framework.permissions import BasePermission, SAFE_METHODS


class StrictRequiresActive(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.profile
            and request.user.profile.is_active
        )


class RequiresActive(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        else:
            return super().has_permission(request, view)


class RequiresPayment(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        else:
            return bool(getattr(request.user, "customer", None))
