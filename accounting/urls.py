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
    path('accounts/<int:pk>/import_pcg/', views.import_pcg, name='account-import-pcg'),
    path('entries/', views.entry_list, name='entry-list'),
    path('entries/import-excel/', views.import_entries_excel, name='entries-import-excel'),
    path('entries/bulk-import/', views.import_entries_bulk, name='entries-bulk-import'),
    path('entries/<int:pk>/', views.entry_list, name='entry-detail'),
    path('api/token/', TokenObtainPairView.as_view(serializer_class=MyTokenObtainPairSerializer), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
