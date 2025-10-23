from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('chat/', views.AccountingChatBotView.as_view(), name='accounting-chat'),
    path('chat/history/<str:session_id>/', views.ChatHistoryView.as_view(), name='chat-history'),
    path('accounting/summary/', views.AccountingSummaryView.as_view(), name='accounting-summary'),
]