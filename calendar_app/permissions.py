from rest_framework import permissions

def is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, "role", None) == "admin"
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        )
    )

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'role', None) == 'student')

class IsTeacherOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, 'role', None) in ['teacher', 'admin']
                or getattr(user, 'is_staff', False)
                or getattr(user, 'is_superuser', False)
            )
        )

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsEduAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, 'role', None) == 'admin'
                or getattr(user, 'is_superuser', False)
            )
        )


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, 'role', None) == 'teacher'
                or getattr(user, 'is_superuser', False)
            )
        )
