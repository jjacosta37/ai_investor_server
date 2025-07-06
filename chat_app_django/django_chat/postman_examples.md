# Django Chat API - Postman/cURL Examples

## Create Chat

```bash
curl --location 'http://127.0.0.1:8000/api/chats/' \
--header 'Content-Type: application/json' \
--data '{
    "title": "My New Chat"
}'
```

## List All Chats

```bash
curl --location 'http://127.0.0.1:8000/api/chats/' \
--header 'Content-Type: application/json'
```

## Get Chat Details

```bash
curl --location 'http://127.0.0.1:8000/api/chats/1/' \
--header 'Content-Type: application/json'
```

## Update Chat

```bash
curl --location --request PUT 'http://127.0.0.1:8000/api/chats/1/' \
--header 'Content-Type: application/json' \
--data '{
    "title": "Updated Chat Title"
}'
```

## Delete Chat (Archive)

```bash
curl --location --request DELETE 'http://127.0.0.1:8000/api/chats/1/' \
--header 'Content-Type: application/json'
```

## Send Message

```bash
curl --location 'http://127.0.0.1:8000/api/chats/1/messages/' \
--header 'Content-Type: application/json' \
--data '{
    "content": "Hello, how are you today?"
}'
```

## Get Chat Messages

```bash
curl --location 'http://127.0.0.1:8000/api/chats/1/messages/' \
--header 'Content-Type: application/json'
```

## Clear Chat Messages

```bash
curl --location --request DELETE 'http://127.0.0.1:8000/api/chats/1/messages/' \
--header 'Content-Type: application/json'
```

## Import to Postman

1. Copy any of the cURL commands above
2. Open Postman
3. Click "Import" in the top left
4. Select "Raw text" tab
5. Paste the cURL command
6. Click "Continue" then "Import"

## Environment Variables (Optional)

For easier testing, you can set up Postman environment variables:

- `base_url`: `http://127.0.0.1:8000`
- `chat_id`: `1` (or any valid chat ID)

Then use `{{base_url}}` and `{{chat_id}}` in your requests.
