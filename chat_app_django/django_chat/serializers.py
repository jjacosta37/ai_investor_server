from rest_framework import serializers
from .models import Chat, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "created_at", "metadata"]
        read_only_fields = ["id", "created_at"]


class ChatListSerializer(serializers.ModelSerializer):
    """Serializer for chat list view (without messages)"""

    message_count = serializers.ReadOnlyField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
            "message_count",
            "last_message_preview",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_last_message_preview(self, obj):
        """Get a preview of the last message"""
        last_message = obj.messages.last()
        if last_message:
            content = last_message.content
            if len(content) > 100:
                content = content[:97] + "..."
            return {
                "role": last_message.role,
                "content": content,
                "created_at": last_message.created_at,
            }
        return None


class ChatDetailSerializer(serializers.ModelSerializer):
    """Serializer for chat detail view (with messages)"""

    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.ReadOnlyField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
            "message_count",
            "messages",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a new message"""

    content = serializers.CharField()

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty.")
        return value.strip()
