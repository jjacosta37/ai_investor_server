# Django Chat App Server

A complete Django server solution for AI-powered chat applications with Firebase authentication. This project provides a robust backend infrastructure combining two reusable Django apps: `django_chat` for chat functionality and `firebase_auth` for Firebase authentication integration.

## Project Overview

This server template is designed to be a reusable foundation for building chat applications with the following architecture:

- **`django_chat`**: Core chat functionality with AI integration
- **`firebase_auth`**: Firebase authentication and user management
- **Frontend-agnostic**: REST API that works with any frontend framework
- **Production-ready**: Includes proper authentication, error handling, and security features

## Features

### Chat Functionality (`django_chat`)

- **Chat Management**: Create, read, update, and delete chat conversations
- **Message Handling**: Send messages and receive AI responses
- **Auto Title Generation**: Automatically generate chat titles from first messages
- **Soft Delete**: Archive chats instead of hard deletion
- **Extensible AI Integration**: Abstract service interface for easy AI provider integration
- **UUID Primary Keys**: Uses UUID instead of integers for better scalability and security

### Authentication (`firebase_auth`)

- **Firebase Authentication**: Secure user authentication using Firebase Auth
- **Token Verification**: Automatic ID token verification for all API requests
- **User Management**: Automatic Django user creation and management
- **Custom Exception Handling**: Comprehensive error handling for auth failures
- **User Deletion**: Secure user deletion across both Django and Firebase

## Architecture

### Authentication Flow

1. Client authenticates with Firebase Auth (frontend)
2. Client receives ID token from Firebase
3. Client includes ID token in `Authorization` header for API requests
4. Server validates token with Firebase Admin SDK
5. Server creates/retrieves corresponding Django user
6. API request proceeds with authenticated user context

### API Structure

- **Explicit Endpoints**: Uses DRF APIView classes for clear, explicit endpoint definitions
- **Token-based Auth**: All API endpoints protected by Firebase authentication
- **RESTful Design**: Follows REST conventions for predictable API behavior
- **Error Handling**: Comprehensive error responses for auth and API failures

## Installation

### Prerequisites

- Python 3.8+
- Django 4.2+
- Firebase project with Authentication enabled
- Firebase Admin SDK service account key

### Setup Instructions

1. **Clone and Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Firebase Configuration**

   - Create a Firebase project at https://console.firebase.google.com
   - Enable Authentication in your Firebase project
   - Generate a service account key:
     - Go to Project Settings → Service Accounts
     - Click "Generate new private key"
     - Save the JSON file in your project root
   - Update the credential path in `settings.py`

3. **Django Configuration**

   Add both apps to your `INSTALLED_APPS`:

   ```python
   INSTALLED_APPS = [
       # ... other apps
       'rest_framework',
       'corsheaders',
       'django_chat',
       'firebase_auth',
   ]
   ```

   Configure DRF authentication:

   ```python
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'firebase_auth.authentication.FirebaseAuthentication',
       ],
   }
   ```

4. **URL Configuration**

   ```python
   from django.urls import path, include

   urlpatterns = [
       path('admin/', admin.site.urls),
       path('api/', include('django_chat.urls')),
       path('auth/', include('firebase_auth.urls')),  # Add this line
   ]
   ```

5. **Environment Variables**
   Create a `.env` file:

   ```
   DJANGO_SECRET_KEY=your_secret_key_here
   ```

6. **Database Migration**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

## API Endpoints

### Authentication Endpoints

- `DELETE /auth/deleteuser/` - Delete current user from both Django and Firebase

### Chat Management Endpoints

All chat endpoints require Firebase authentication.

#### Chat Operations

- `GET /api/chats/` - List all chats for authenticated user
- `POST /api/chats/` - Create a new chat
- `GET /api/chats/{uuid}/` - Get chat details with messages
- `PUT /api/chats/{uuid}/` - Update chat (e.g., title)
- `DELETE /api/chats/{uuid}/` - Archive chat

#### Message Operations

- `GET /api/chats/{uuid}/messages/` - Get all messages for a chat
- `POST /api/chats/{uuid}/messages/` - Send message and get AI response
- `DELETE /api/chats/{uuid}/messages/` - Clear all messages from chat

## Frontend Integration

### Authentication Setup

Your frontend needs to:

1. Initialize Firebase Auth
2. Handle user login/logout
3. Include the ID token in API requests

### Example Frontend Implementation

#### Firebase Setup (JavaScript)

```javascript
// firebase-config.js
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  // Your Firebase config
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

#### API Client with Authentication

```javascript
// api-client.js
import { auth } from "./firebase-config";

class ChatAPI {
  async getAuthToken() {
    const user = auth.currentUser;
    if (!user) throw new Error("User not authenticated");
    return await user.getIdToken();
  }

  async makeAuthenticatedRequest(url, options = {}) {
    const token = await this.getAuthToken();
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
  }

  async getChats() {
    const response = await this.makeAuthenticatedRequest("/api/chats/");
    return response.json();
  }

  async createChat(title = "") {
    const response = await this.makeAuthenticatedRequest("/api/chats/", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
    return response.json();
  }

  async sendMessage(chatId, content) {
    const response = await this.makeAuthenticatedRequest(
      `/api/chats/${chatId}/messages/`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      }
    );
    return response.json();
  }
}

export const chatAPI = new ChatAPI();
```

#### React Example

```jsx
// components/ChatApp.jsx
import { useEffect, useState } from "react";
import {
  signInWithEmailAndPassword,
  onAuthStateChanged,
  signOut,
} from "firebase/auth";
import { auth } from "../firebase-config";
import { chatAPI } from "../api-client";

function ChatApp() {
  const [user, setUser] = useState(null);
  const [chats, setChats] = useState([]);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      if (user) {
        loadChats();
      }
    });
    return unsubscribe;
  }, []);

  const loadChats = async () => {
    try {
      const chatsData = await chatAPI.getChats();
      setChats(chatsData);
    } catch (error) {
      console.error("Error loading chats:", error);
    }
  };

  const handleLogin = async (email, password) => {
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (error) {
      console.error("Login error:", error);
    }
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      setChats([]);
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  if (!user) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <div>
      <header>
        <h1>Chat App</h1>
        <button onClick={handleLogout}>Logout</button>
      </header>
      <ChatList chats={chats} />
    </div>
  );
}
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

Then update the `get_chat_service()` function in `django_chat/services.py`:

```python
def get_chat_service():
    from myproject.services import MyAIService
    return MyAIService()
```

## Security Considerations

- **Token Validation**: All requests are validated against Firebase Auth
- **User Isolation**: Users can only access their own chats and messages
- **Secure Deletion**: User deletion removes data from both Django and Firebase
- **CORS Configuration**: Properly configure CORS for your frontend domains
- **Environment Variables**: Keep sensitive data in environment variables

## Error Handling

The authentication system provides comprehensive error handling:

- **`NoAuthToken`**: 401 - No authentication token provided
- **`InvalidAuthToken`**: 401 - Invalid authentication token
- **`FirebaseError`**: 500 - Firebase-related errors

## Development

### Running the Server

```bash
python manage.py runserver
```

### Testing Authentication

Use tools like Postman or curl to test the API:

```bash
# Get ID token from Firebase Auth in your frontend
curl -H "Authorization: Bearer YOUR_FIREBASE_ID_TOKEN" \
     http://localhost:8000/api/chats/
```

## Data Models

### Chat Model

- `title`: Chat title (auto-generated or user-set)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `is_archived`: Soft deletion flag
- `user`: Foreign key to Django User (automatically set based on Firebase auth)

### Message Model

- `chat`: Foreign key to Chat
- `role`: 'user', 'assistant', or 'system'
- `content`: Message content
- `created_at`: Creation timestamp
- `metadata`: JSON field for additional data

## Requirements

- Django >= 4.2
- Django REST Framework >= 3.14
- django-cors-headers
- django-environ
- firebase-admin
- Python >= 3.8

## License

This project is designed to be a reusable template for chat applications. Customize as needed for your specific use case.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

This is a template project designed for customization. For Firebase-specific issues, refer to the [Firebase documentation](https://firebase.google.com/docs). For Django-related questions, see the [Django documentation](https://docs.djangoproject.com/).
