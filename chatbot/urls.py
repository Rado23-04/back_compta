from django.urls import path
from .views import (
    AccountingChatBotView, 
    GeminiStatusView, 
    ChatHistoryView, 
    AccountingSummaryView, 
    ConversationListView,
    CreateConversationView
)

urlpatterns = [
    # Endpoint principal du chatbot
    path('chat/', AccountingChatBotView.as_view(), name='accounting_chat'),
    
    # Statut de Gemini
    path('gemini-status/', GeminiStatusView.as_view(), name='gemini_status'),
    
    # Historique des conversations
    path('chat/history/<str:session_id>/', ChatHistoryView.as_view(), name='chat_history'),
    
    # Liste toutes les conversations
    path('conversations/', ConversationListView.as_view(), name='conversation_list'),
    
    # Créer une nouvelle conversation
    path('conversations/create/', CreateConversationView.as_view(), name='create_conversation'),
    
    # Résumé comptable
    path('accounting-summary/', AccountingSummaryView.as_view(), name='accounting_summary'),
]