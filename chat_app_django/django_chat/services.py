from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseChatService(ABC):
    """
    Abstract base class for chat AI services.
    Projects should inherit from this class and implement the required methods.
    """

    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate AI response based on conversation history.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional parameters for the AI service

        Returns:
            str: The AI response content
        """
        pass

    @abstractmethod
    def generate_title(self, first_message: str) -> str:
        """
        Generate a chat title based on the first user message.

        Args:
            first_message: The first user message content

        Returns:
            str: Generated title for the chat
        """
        pass


class DefaultChatService(BaseChatService):
    """
    Default implementation that returns placeholder responses.
    Replace this with your actual AI service implementation.
    """

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Default implementation returns a placeholder response."""
        return "This is a placeholder response. Please implement your AI service."

    def generate_title(self, first_message: str) -> str:
        """Default implementation generates simple titles."""
        # Take first few words of the message
        words = first_message.split()[:4]
        title = " ".join(words)
        if len(title) > 30:
            title = title[:27] + "..."
        return title or "New Chat"


def get_chat_service() -> BaseChatService:
    """
    Factory function to get the configured chat service.
    This can be extended to read from Django settings.
    """
    # For now, return the default service
    # In the future, this could read from settings:
    # service_class = getattr(settings, 'DJANGO_CHAT_SERVICE_CLASS', DefaultChatService)
    return DefaultChatService()
