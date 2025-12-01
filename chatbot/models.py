# models.py - Gardez exactement votre code actuel
from django.db import models
from django.utils import timezone
from django.conf import settings

class ChatConversation(models.Model):
    """Modèle pour sauvegarder chaque conversation"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200, default="Nouvelle conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
    
    def __str__(self):
        return f"{self.title} ({self.session_id})"
    
    def update_title_from_messages(self):
        """Met à jour le titre basé sur le premier message utilisateur"""
        first_user_message = self.messages.filter(message_type='USER').first()
        if first_user_message:
            title = first_user_message.content
            if len(title) > 50:
                title = title[:47] + "..."
            self.title = title
            self.save()
    
    def get_message_count(self):
        return self.messages.count()
    
    def get_last_activity(self):
        last_message = self.messages.last()
        return last_message.timestamp if last_message else self.updated_at

class ChatMessage(models.Model):
    """Modèle pour sauvegarder chaque message"""
    MESSAGE_TYPES = [
        ('USER', 'Message utilisateur'),
        ('BOT', 'Message bot'),
        ('SYSTEM', 'Message système'),
    ]
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    conversation = models.ForeignKey(
        ChatConversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    sql_query_used = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    tokens_used = models.IntegerField(default=0)
    processing_time = models.FloatField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        if self.conversation:
            self.conversation.updated_at = timezone.now()
            self.conversation.save()
        super().save(*args, **kwargs)