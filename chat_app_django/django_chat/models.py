import uuid
from django.db import models
from django.contrib.auth.models import User


# ==============================
# SECTION: Base Model used so models have UUID as the primary key
# ==============================


class DjangoBaseModel(models.Model):
    """
    An abstract base class model that provides a UUID as the primary key.

    This model is designed to be inherited by other models in the project.
    By inheriting from this base model, derived models will automatically
    get a UUID primary key named 'id'.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique UUID identifier for the model.",
    )

    class Meta:
        # This ensures Django won't create a table for BaseModel.
        abstract = True


class Chat(DjangoBaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats")
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Chat {self.id}"

    @property
    def message_count(self):
        return self.messages.count()

    def get_first_user_message(self):
        """Get the first user message for auto-generating titles"""
        return self.messages.filter(role="user").first()


class Message(DjangoBaseModel):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return f"{self.role}: {content_preview}"
