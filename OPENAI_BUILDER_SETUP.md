# OpenAI Agent Builder Setup Guide

## Important: MCP HTTP Support

**Update**: OpenAI Agent Builder (web version) does **NOT** currently support custom MCP servers over HTTP. The MCP endpoints we created are for:
- Future compatibility when HTTP transport is supported
- Desktop MCP clients (Claude Desktop, future OpenAI Desktop)
- Custom integrations

## ✅ Working Method: Use OpenAPI Actions

OpenAI Agent Builder **does** support OpenAPI schemas. Use this method:

### Step 1: Get Your OpenAPI Schema

Your server exposes an OpenAPI schema at:
```
https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json
```

### Step 2: Import into Agent Builder

1. Open your Agent in **OpenAI Agent Builder**
2. Click **"Configure"** or **"Actions"** section
3. Look for **"Import from URL"** or **"Add Action"**
4. Paste the OpenAPI URL:
   ```
   https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json
   ```
5. Click **Import**

The Agent Builder will automatically:
- Parse the OpenAPI schema
- Create an action for `summarize_emails`
- Configure the correct endpoint, parameters, and authentication

### Step 3: Configure Agent Instructions

Add to your agent's system prompt:
```
You have access to an email summarization tool. When the user asks about their emails 
from a specific date or time range, use the summarize_emails action with proper ISO 
timestamps in UTC timezone (ending with Z).

Examples:
- "emails from November 9th" → use 2025-11-09T00:00:00Z to 2025-11-09T23:59:59Z
- "emails from last week" → calculate the date range and use ISO format
```

### Step 4: Test

Try asking:
- "Summarize my emails from November 9th, 2025"
- "What emails did I receive on June 5th, 2024?"
- "Check my emails from yesterday"

---

## Alternative: Manual Action Configuration

If OpenAPI import doesn't work, configure manually:

### Action Details:

**Name**: `summarize_emails`

**Description**: 
```
Fetches and summarizes emails from a mailbox within a specified time range. 
Requires ISO 8601 timestamps with UTC timezone (ending in Z).
```

**Authentication**: None (or API key if you add one)

**Schema**:
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Email Summarization API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://hellen-sarraceniaceous-adelina.ngrok-free.dev"
    }
  ],
  "paths": {
    "/tool/read_emails": {
      "post": {
        "operationId": "summarize_emails",
        "summary": "Summarize emails in time range",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "intent": {
                    "type": "string",
                    "enum": ["summarize_emails"]
                  },
                  "absolute_time_range": {
                    "type": "object",
                    "properties": {
                      "start_iso": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format with UTC (e.g., '2025-11-09T00:00:00Z')"
                      },
                      "end_iso": {
                        "type": "string",
                        "description": "End time in ISO 8601 format with UTC (e.g., '2025-11-09T23:59:59Z')"
                      }
                    },
                    "required": ["start_iso", "end_iso"]
                  }
                },
                "required": ["intent", "absolute_time_range"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Email summary"
          }
        }
      }
    }
  }
}
```

---

## MCP Endpoints (For Desktop Clients)

The MCP protocol endpoints are available but **not used by web-based Agent Builder**:

- `POST /mcp/v1/initialize` - Handshake
- `POST /mcp/v1/tools/list` - Tool discovery  
- `POST /mcp/v1/tools/call` - Tool execution

These work with:
- **Claude Desktop** (if configured with HTTP transport)
- **Future OpenAI Desktop** app
- **Custom MCP clients**

To use MCP endpoints in desktop apps, they would need to support HTTP transport (most use stdio currently).

---

## Debugging

### Check if Action is Registered

In Agent Builder:
1. Go to **Configure** → **Actions**
2. You should see `summarize_emails` listed
3. Click to view the schema

### Test the Action

In the Agent Builder chat:
```
Use the summarize_emails action to check emails from November 9th, 2025
```

### View ngrok Requests

Open in browser:
```
http://127.0.0.1:4040
```

This shows all incoming HTTP requests to your Flask server, so you can see if Agent Builder is calling it.

### Common Issues

1. **ngrok URL expired**: Free ngrok URLs expire. Restart with `./start_ngrok.sh`
2. **Wrong date format**: Agent must use ISO 8601 with Z suffix
3. **Action not called**: Agent didn't understand intent - be more explicit
4. **CORS errors**: Should be fixed (CORS enabled for `platform.openai.com`)

---

## Summary

**For OpenAI Agent Builder (Web):**
✅ Use OpenAPI schema import: `https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json`

**For Desktop MCP Clients:**
✅ Use MCP endpoints: Base URL `https://hellen-sarraceniaceous-adelina.ngrok-free.dev`

**Don't use:**
❌ Trying to register base URL as "MCP Server" in web Agent Builder (not supported yet)
