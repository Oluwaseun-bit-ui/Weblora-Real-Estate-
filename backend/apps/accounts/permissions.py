from rest_framework.permissions import BasePermission


class IsVerificationOfficerOrAbove(BasePermission):
    """Allows access to verification officers, support staff and superadmins."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or getattr(user, "is_staff_role", False))
        )


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.role == user.Role.SUPERADMIN))
