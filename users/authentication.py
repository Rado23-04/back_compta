from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom authentication class that reads the access token from a cookie
    named 'access' instead of the Authorization header. It reuses the
    validation logic from SimpleJWT's JWTAuthentication.

    If no cookie is present, it returns None so other authentication
    classes may be attempted.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get('access')
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except Exception as exc:
            raise exceptions.AuthenticationFailed('Invalid or expired token') from exc

        try:
            user = self.get_user(validated_token)
        except Exception as exc:
            raise exceptions.AuthenticationFailed('User not found') from exc

        return (user, validated_token)
