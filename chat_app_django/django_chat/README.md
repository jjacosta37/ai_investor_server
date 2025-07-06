# Django Chat App

A reusable Django app for building AI-powered chat applications. This app provides the backend infrastructure for chat functionality with a clean API that can be integrated with any frontend framework.

## Features

- **Chat Management**: Create, read, update, and delete chat conversations
- **Message Handling**: Send messages and receive AI responses
- **Auto Title Generation**: Automatically generate chat titles from first messages
- **Soft Delete**: Archive chats instead of hard deletion
- **Extensible AI Integration**: Abstract service interface for easy AI provider integration
- **REST API**: Full REST API using Django REST Framework APIView classes
- **Admin Interface**: Django admin integration for easy management
- **Explicit Endpoints**: Uses APIView classes for clear, explicit endpoint definitions
- **UUID Primary Keys**: Uses UUID instead of integers for better scalability and security

## Architecture

This app uses Django REST Framework's `APIView` classes instead of ViewSets, providing:

- **Explicit Control**: Each endpoint is clearly defined with its own class and methods
- **Easy Customization**: Simple to override specific HTTP methods or add custom logic
- **Clear Structure**: Easy to understand and maintain the API structure
- **Flexible**: Easy to add custom endpoints or modify existing ones
- **UUID-based**: All models use UUID primary keys for better distributed system support

## Installation

1. Add `django_chat` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'django_chat',
]
```

2. Include the URLs in your project's URL configuration:

```python
from django.urls import path, include

urlpatterns = [
    # ... other URLs
    path('', include('django_chat.urls')),
]
```

3. Run migrations:

```bash
python manage.py makemigrations django_chat
python manage.py migrate
```

## API Endpoints

### Chat Management

- `GET /api/chats/` - List all chats
- `POST /api/chats/` - Create a new chat
- `GET /api/chats/{uuid}/` - Get chat details with messages
- `PUT /api/chats/{uuid}/` - Update chat (e.g., title)
- `DELETE /api/chats/{uuid}/` - Archive chat

### Messages (Consolidated Endpoint)

- `GET /api/chats/{uuid}/messages/` - Get all messages for a chat
- `POST /api/chats/{uuid}/messages/` - Send message and get AI response
- `DELETE /api/chats/{uuid}/messages/` - Clear all messages from chat

## Usage Examples

### Creating a New Chat

```javascript
const response = await fetch("/api/chats/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    title: "My New Chat",
  }),
});
const chat = await response.json();
```

### Sending a Message

```javascript
const response = await fetch(`/api/chats/${chatId}/messages/`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    content: "Hello, how are you?",
  }),
});
const result = await response.json();
// result contains user_message, ai_message, and updated chat data
// Note: chatId should be a UUID like "550e8400-e29b-41d4-a716-446655440000"
```

### Getting Chat Messages

```javascript
const response = await fetch(`/api/chats/${chatId}/messages/`);
const messages = await response.json();
```

### Clearing Chat Messages

```javascript
const response = await fetch(`/api/chats/${chatId}/messages/`, {
  method: "DELETE",
});
const result = await response.json();
// result: {"message": "Chat cleared successfully"}
```

### Getting Chat List

```javascript
const response = await fetch("/api/chats/");
const chats = await response.json();
```

## AI Service Integration

To integrate your own AI service, create a class that inherits from `BaseChatService`:

```python
# myproject/services.py
from django_chat.services import BaseChatService

class MyAIService(BaseChatService):
    def generate_response(self, messages, **kwargs):
        # Implement your AI logic here
        # messages is a list of {'role': 'user/assistant', 'content': 'message'}
        return "Your AI response here"

    def generate_title(self, first_message):
        # Generate a title from the first message
        return f"Chat about {first_message[:30]}..."
```

Then update the `get_chat_service()` function in `django_chat/services.py` to return your service:

```python
def get_chat_service():
    from myproject.services import MyAIService
    return MyAIService()
```

## Data Models

### Chat Model

- `title`: Chat title (auto-generated or user-set)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `is_archived`: Soft deletion flag

### Message Model

- `chat`: Foreign key to Chat
- `role`: 'user', 'assistant', or 'system'
- `content`: Message content
- `created_at`: Creation timestamp
- `metadata`: JSON field for additional data

## Frontend Integration

This app is designed to work with any frontend framework. The API follows REST conventions and returns JSON responses suitable for React, Vue, Angular, or vanilla JavaScript applications.

### Example React Integration

```javascript
// api/chat.js
export const chatAPI = {
  async getChats() {
    const response = await fetch("/api/chats/");
    return response.json();
  },

  async createChat(title = "") {
    const response = await fetch("/api/chats/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    return response.json();
  },

  async sendMessage(chatId, content) {
    const response = await fetch(`/api/chats/${chatId}/messages/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    return response.json();
  },
};
```

## Development

For development, the app includes a default service that returns placeholder responses. Replace this with your actual AI service implementation.

## Requirements

- Django >= 4.2
- Django REST Framework >= 3.14
- Python >= 3.8

## License

This app is designed to be reusable across projects. Customize as needed for your specific use case.
