# Authentication Setup Guide

## Quick Setup for OpenAI Builder

### 1. Generate API Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output: `Kx9vZ2mP4wQ8jR5nT3fH7aL1cB6yU0sD2eW9hM8gN5k`

### 2. Add to .env file

Edit `/Users/frank/projects/ai-agent/imap-email-mcp/.env` and add:

```bash
MCP_API_KEY=Kx9vZ2mP4wQ8jR5nT3fH7aL1cB6yU0sD2eW9hM8gN5k
```

### 3. Restart your MCP server

```bash
./start_server.sh
```

You should see:
```
[INFO] MCP API Key authentication enabled
```

### 4. Start ngrok (without basic auth)

```bash
./start_ngrok.sh frankimap.ngrok.dev
```

Note: No need for ngrok basic auth since we're using API key auth at the MCP level.

### 5. Configure in OpenAI Builder

In OpenAI Builder, when adding your MCP server:

- **Server URL**: `https://frankimap.ngrok.dev/sse`
- **Authentication Method**: Select **"Access Token/API key"**
- **API Key**: Paste your `MCP_API_KEY` value (e.g., `Kx9vZ2mP4wQ8jR5nT3fH7aL1cB6yU0sD2eW9hM8gN5k`)

## How It Works

1. OpenAI sends the API key in the `Authorization` header
2. Your MCP server validates it against `MCP_API_KEY` in `.env`
3. If valid, request proceeds; if not, returns 401 Unauthorized

## Security Notes

- ✅ Use API key authentication (MCP level)
- ❌ Skip ngrok basic auth (not compatible with OpenAI Builder's auth headers)
- 🔒 Keep your `MCP_API_KEY` secret
- 🔄 Rotate the key periodically
- 📝 Never commit `.env` to git

## Testing

Test your authentication with curl:

```bash
# Should fail (no auth)
curl https://frankimap.ngrok.dev/sse

# Should succeed
curl -H "Authorization: Bearer YOUR_API_KEY" https://frankimap.ngrok.dev/sse
```
