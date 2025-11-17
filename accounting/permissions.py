from rest_framework import permissions


class IsAdminComptableOrReadCreateOnly(permissions.BasePermission):
    """Custom permission:

    - SAFE_METHODS (GET, HEAD, OPTIONS) allowed for authenticated users.
    - POST allowed for users with role 'comptable' or 'admin-comptable'.
    - PUT/PATCH/DELETE allowed only for users with role 'admin-comptable'.
    """

    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        # Ensure user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow safe methods for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow POST for comptable and admin-comptable
        if request.method == 'POST':
            return getattr(request.user, 'role', None) in ('comptable', 'admin-comptable')

        # Allow PUT/PATCH/DELETE only for admin-comptable
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            return getattr(request.user, 'role', None) == 'admin-comptable'

        return False
