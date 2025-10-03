from django.urls import path
from . import views

# URLs pour l'API comptable
urlpatterns = [
    # Gestion des comptes
    path('accounts/', views.account_list, name='account-list'),  # /api/accounts/
    
    # Gestion des écritures
    path('entries/', views.entry_list, name='entry-list'),      # /api/entries/
    
    # Bilan et analyses
    path('balance-sheet/', views.balance_sheet, name='balance-sheet'),  # /api/balance-sheet/
    path('accounts/<int:account_id>/statement/', views.account_statement, name='account-statement'),  # /api/accounts/1/statement/
]
