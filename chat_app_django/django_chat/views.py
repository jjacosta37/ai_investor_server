from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Chat, Message
from .serializers import (
    ChatListSerializer,
    ChatDetailSerializer,
    MessageSerializer,
    SendMessageSerializer,
)
from .services import get_chat_service
from firebase_auth.authentication import FirebaseAuthentication
from rest_framework.permissions import IsAuthenticated


class ChatListView(APIView):
    """
    List all chats or create a new chat for the authenticated user.
    """

    def get(self, request):
        """Get list of all chats for the authenticated user"""
        chats = Chat.objects.filter(user=request.user, is_archived=False)
        serializer = ChatListSerializer(chats, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new chat for the authenticated user"""
        serializer = ChatDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatDetailView(APIView):
    """
    Retrieve, update or delete a specific chat for the authenticated user.
    """

    def get_object(self, pk, user):
        """Get chat object for the authenticated user or return 404"""
        return get_object_or_404(Chat, pk=pk, user=user, is_archived=False)

    def get(self, request, pk):
        """Get chat details with messages for the authenticated user"""
        chat = self.get_object(pk, request.user)
        serializer = ChatDetailSerializer(chat)
        return Response(serializer.data)

    def put(self, request, pk):
        """Update chat (e.g., title) for the authenticated user"""
        chat = self.get_object(pk, request.user)
        serializer = ChatDetailSerializer(chat, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Archive chat (soft delete) for the authenticated user"""
        chat = self.get_object(pk, request.user)
        chat.is_archived = True
        chat.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatMessagesView(APIView):
    """
    Handle chat messages for the authenticated user: GET (list messages), POST (send message), DELETE (clear all messages).
    """

    def get_object(self, pk, user):
        """Get chat object for the authenticated user or return 404"""
        return get_object_or_404(Chat, pk=pk, user=user, is_archived=False)

    def get(self, request, pk):
        """Get all messages for a chat owned by the authenticated user"""
        chat = self.get_object(pk, request.user)
        messages = chat.messages.all()

        # You can add pagination here if needed
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        """Send a message to chat owned by the authenticated user and get AI response"""
        chat = self.get_object(pk, request.user)
        serializer = SendMessageSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_content = serializer.validated_data["content"]

        try:
            with transaction.atomic():
                # Create user message
                user_message = Message.objects.create(
                    chat=chat, role="user", content=user_content
                )

                # Generate title if this is the first user message
                if not chat.title and chat.message_count == 1:
                    chat_service = get_chat_service()
                    chat.title = chat_service.generate_title(user_content)
                    chat.save()

                # Prepare message history for AI
                messages = []
                for msg in chat.messages.all():
                    messages.append({"role": msg.role, "content": msg.content})

                # Generate AI response
                chat_service = get_chat_service()
                ai_response = chat_service.generate_response(messages)

                # Create AI message
                ai_message = Message.objects.create(
                    chat=chat, role="assistant", content=ai_response
                )

                # Update chat timestamp
                chat.save()  # This will update the updated_at field

                # Return both messages
                return Response(
                    {
                        "user_message": MessageSerializer(user_message).data,
                        "ai_message": MessageSerializer(ai_message).data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            return Response(
                {"error": f"Failed to process message: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, pk):
        """Clear all messages from a chat owned by the authenticated user"""
        chat = self.get_object(pk, request.user)
        chat.messages.all().delete()
        chat.title = ""  # Reset title
        chat.save()

        return Response(
            {"message": "Chat cleared successfully"}, status=status.HTTP_200_OK
        )
