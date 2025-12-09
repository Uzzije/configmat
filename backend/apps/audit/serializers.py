from rest_framework import serializers
from .models import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'user_name', 'user_email', 'action', 'target', 'details', 'created_at']
        read_only_fields = fields

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return "System"

    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return ""
