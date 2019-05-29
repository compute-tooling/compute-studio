from rest_framework.permissions import BasePermission, SAFE_METHODS


class RequiresActive(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.profile and request.user.profile.is_active)


class RequiresPayment(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.customer)
