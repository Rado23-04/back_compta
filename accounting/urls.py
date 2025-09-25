from django.urls import path
from . import views

# URL pour lister et créer des comptes
urlpatterns = [
    path('accounts/', views.account_list, name='account-list'),  # /api/accounts/
    path('entries/', views.entry_list, name='entry-list'),      # /api/entries/
]
