from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import ChatMessage
from .serializers import ChatMessageSerializer

class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ChatMessage.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Mark all admin messages as read"""
        ChatMessage.objects.filter(
            user=request.user,
            is_from_admin=True,
            read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({"status": "marked read"})
        
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = ChatMessage.objects.filter(
            user=request.user,
            is_from_admin=True,
            read_at__isnull=True
        ).count()
        return Response({"count": count})
