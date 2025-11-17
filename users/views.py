from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

User = get_user_model()


def get_tokens_for_user(user):
    """Return both refresh and access tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = get_tokens_for_user(user)
        data = {
            'token': token,
            'user': UserSerializer(user).data,
        }
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')

        # Try authenticate using email kwarg (works with custom USERNAME_FIELD='email')
        user = authenticate(request, email=email, password=password)
        if user is None:
            # fallback to username param for compatibility
            user = authenticate(request, username=email, password=password)

        if user is None:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        tokens = get_tokens_for_user(user)

        data = {
            # Keep returning token in body for non-browser clients; frontend can ignore it
            'token': tokens['access'],
            'user': UserSerializer(user).data,
        }

        # Build response and set HttpOnly cookies for access and refresh
        response = Response(data, status=status.HTTP_200_OK)

        # Cookie params
        access_max_age = int(settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME').total_seconds())
        refresh_max_age = int(settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME').total_seconds())

        # In production, SECURE should be True and SameSite=None for cross-site cookies.
        # For local development (DEBUG=True) we relax secure to False so cookies can be set over HTTP.
        secure_flag = not settings.DEBUG
        samesite_val = 'None' if secure_flag else 'Lax'

        # Set cookies (HttpOnly) so JavaScript cannot read them (mitigates XSS)
        response.set_cookie(
            key='access',
            value=tokens['access'],
            httponly=True,
            secure=secure_flag,
            samesite=samesite_val,
            max_age=access_max_age,
            path='/',
        )
        response.set_cookie(
            key='refresh',
            value=tokens['refresh'],
            httponly=True,
            secure=secure_flag,
            samesite=samesite_val,
            max_age=refresh_max_age,
            path='/',
        )

        return response


class LogoutView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        # To logout, remove cookies by setting max_age=0
        response = Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        response.delete_cookie('access', path='/')
        response.delete_cookie('refresh', path='/')
        return response


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        return Response(UserSerializer(user).data)
