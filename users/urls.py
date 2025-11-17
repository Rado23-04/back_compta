from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import RegisterView, LoginView, MeView, LogoutView
from .serializers import MyTokenObtainPairSerializer

# Use trailing slashes on auth endpoints so frontend requests to e.g. /api/auth/login/
# (with a trailing slash) will match. This is the conventional Django style.
urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    # Alias historique pour compatibilité frontend
    path('signup/', RegisterView.as_view(), name='auth-signup'),
    path('login/', LoginView.as_view(), name='auth-login'),  #http://127.0.0.1:8000/api/auth/login/
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    # Token endpoint using custom serializer that injects 'role' into JWT payload
    path('token/', TokenObtainPairView.as_view(serializer_class=MyTokenObtainPairSerializer), name='token_obtain_pair'),
]
