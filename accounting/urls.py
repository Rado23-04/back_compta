from django.urls import path
from django.conf.urls.static import static
from . import views
from back_compta import settings


# URL pour lister et créer des comptes
urlpatterns = [
    path('accounts/', views.account_list, name='account-list'),
    path('accounts/<int:pk>/', views.account_list, name='account-detail'),
    path('entries/', views.entry_list, name='entry-list'),
    path('entries/<int:pk>/', views.entry_list, name='entry-detail'),
    path('import/', views.importing, name='import')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
