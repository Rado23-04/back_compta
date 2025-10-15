from django.urls import path
from . import views

# URL pour lister et créer des comptes
urlpatterns = [
    path('accounts/', views.account_list, name='account-list'),
    path('accounts/<int:pk>/', views.account_list, name='account-detail'),
    path('entries/', views.entry_list, name='entry-list'),
    path('entries/<int:pk>/', views.entry_list, name='entry-detail'),
]
