from rest_framework import serializers
from .models import ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'message', 'is_from_admin', 'created_at', 'read_at']
        read_only_fields = ['id', 'is_from_admin', 'created_at', 'read_at']
