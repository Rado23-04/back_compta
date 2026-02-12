# Dans urls.py
from django.urls import path
from .views import (
    AccountingChatBotView, GeminiStatusView, ChatHistoryView,
    AccountingSummaryView, ConversationListView, CreateConversationView,
    CleanEmptyConversationsView  # Nouvelle vue
)

urlpatterns = [
    path('chat/', AccountingChatBotView.as_view(), name='chat'),
    path('chat/status/', GeminiStatusView.as_view(), name='gemini_status'),
    path('chat/history/<str:session_id>/', ChatHistoryView.as_view(), name='chat_history'),
    path('summary/', AccountingSummaryView.as_view(), name='accounting_summary'),
    path('conversations/', ConversationListView.as_view(), name='conversation_list'),
    path('conversations/create/', CreateConversationView.as_view(), name='create_conversation'),
    path('conversations/clean/', CleanEmptyConversationsView.as_view(), name='clean_conversations'),  # Nouvelle URL
]