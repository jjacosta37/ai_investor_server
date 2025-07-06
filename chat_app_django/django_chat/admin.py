from django.contrib import admin
from .models import Chat, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["created_at"]
    fields = ["role", "content", "created_at"]


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "title",
        "message_count",
        "created_at",
        "updated_at",
        "is_archived",
    ]
    list_filter = ["is_archived", "created_at", "updated_at", "user"]
    search_fields = ["title", "user__username"]
    readonly_fields = ["created_at", "updated_at", "message_count"]
    inlines = [MessageInline]

    def message_count(self, obj):
        return obj.message_count

    message_count.short_description = "Messages"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "chat", "chat_user", "role", "content_preview", "created_at"]
    list_filter = ["role", "created_at", "chat__user"]
    search_fields = ["content", "chat__title", "chat__user__username"]
    readonly_fields = ["created_at"]

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    def chat_user(self, obj):
        return obj.chat.user.username

    content_preview.short_description = "Content Preview"
    chat_user.short_description = "Chat User"
