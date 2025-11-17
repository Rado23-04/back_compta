from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from users.serializers import MyTokenObtainPairSerializer

# URL pour lister et créer des comptes
urlpatterns = [
    path('accounts/', views.account_list, name='account-list'),
    path('accounts/<int:pk>/', views.account_list, name='account-detail'),
    path('entries/', views.entry_list, name='entry-list'),
    path('entries/<int:pk>/', views.entry_list, name='entry-detail'),
    path('api/token/', TokenObtainPairView.as_view(serializer_class=MyTokenObtainPairSerializer), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
