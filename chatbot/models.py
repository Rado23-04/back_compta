from django.db import models
from django.contrib.auth.models import User

class ChatConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chatbot_conversation'
        ordering = ['-created_at']

    def __str__(self):
        return f"Conversation {self.session_id}"

class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('USER', 'User'),
        ('BOT', 'Bot'),
    ]
    
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    sql_query_used = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'chatbot_message'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message_type} - {self.timestamp}"