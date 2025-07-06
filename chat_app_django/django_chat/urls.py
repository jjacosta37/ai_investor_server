from django.urls import path
from .views import (
    ChatListView,
    ChatDetailView,
    ChatMessagesView,
)

app_name = "django_chat"

urlpatterns = [
    # Chat management endpoints
    path("chats/", ChatListView.as_view(), name="chat-list"),
    path("chats/<uuid:pk>/", ChatDetailView.as_view(), name="chat-detail"),
    # Message endpoints - consolidated under one view
    path(
        "chats/<uuid:pk>/messages/",
        ChatMessagesView.as_view(),
        name="chat-messages",
    ),
]
