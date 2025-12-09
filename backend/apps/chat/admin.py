from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_from_admin', 'created_at', 'read_at')
    list_filter = ('is_from_admin', 'created_at')
    search_fields = ('user__email', 'message')
    readonly_fields = ('created_at',)
    
    def save_model(self, request, obj, form, change):
        if not change: # Creating new message
            # If admin creates a message, assume it's a reply to the user selected
            obj.is_from_admin = True
        super().save_model(request, obj, form, change)
