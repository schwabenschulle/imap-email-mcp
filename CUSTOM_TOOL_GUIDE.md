# Custom Tool Definition for OpenAI Agent Builder

## MCP Protocol Integration (Recommended)

Your Flask server now supports the **Model Context Protocol (MCP)** over HTTP! 

### Register MCP Server in Agent Builder

1. In Agent Builder, look for **MCP Server** or **External Server** configuration
2. Register the base URL:
```
https://hellen-sarraceniaceous-adelina.ngrok-free.dev
```

The Agent Builder will automatically:
- Call `/mcp/v1/initialize` to connect
- Call `/mcp/v1/tools/list` to discover the `summarize_emails` tool
- Call `/mcp/v1/tools/call` when you ask about emails

### MCP Endpoints Available

✅ **POST /mcp/v1/initialize** - Protocol handshake  
✅ **POST /mcp/v1/tools/list** - Tool discovery  
✅ **POST /mcp/v1/tools/call** - Tool execution  

### Tool Schema

The `summarize_emails` tool accepts:
- `start_iso` (string): Start time, e.g., `"2025-11-09T00:00:00Z"`
- `end_iso` (string): End time, e.g., `"2025-11-09T23:59:59Z"`

---

## Alternative: HTTP Action (If MCP Not Supported)

If your Agent Builder doesn't support MCP servers yet, use the direct HTTP endpoint:

### Method 1: HTTP Action (Recommended)

1. In Agent Builder, click **Tools** → **+ Add**
2. Choose **"Action"** or **"HTTP"**
3. Configure:

**Action Name**: `summarize_emails`

**Description**: 
```
Read and summarize emails from mailbox in specified time range. Accepts ISO 8601 timestamps with UTC timezone (ending in Z).
```

**HTTP Method**: `POST`

**URL**: 
```
https://hellen-sarraceniaceous-adelina.ngrok-free.dev/tool/read_emails
```

**Headers**:
```json
{
  "Content-Type": "application/json"
}
```

**Body (JSON)**:
```json
{
  "intent": "summarize_emails",
  "absolute_time_range": {
    "start_iso": "{{start_iso}}",
    "end_iso": "{{end_iso}}"
  }
}
```

**Parameters**:
- `start_iso` (string, required): Start time in ISO format, e.g., "2024-06-05T00:00:00Z"
- `end_iso` (string, required): End time in ISO format, e.g., "2024-06-05T23:59:59Z"

### Method 2: Import OpenAPI Schema

If your Agent Builder supports OpenAPI import:

1. Click **Actions** → **Import from URL**
2. Enter: `https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json`
3. Click **Import**

This will automatically configure everything!

## Step-by-Step in Agent Builder

1. **Click "Tools" section** (right panel)
2. **Click "+ Add"** next to Tools
3. **Select "Custom function"** or "Function"
4. **Function Name**: `summarize_emails`
5. **Description**: "Read and summarize emails from mailbox in specified time range using ISO timestamps"
6. **Parameters**: Paste the JSON schema above
7. **Implementation**: Paste the JavaScript code above
8. **Test**: Try calling it with sample dates

## Testing Your Custom Tool

Once added, try asking the agent:

- "Summarize my emails from June 5th, 2024"
- "Check emails between 2024-06-05 00:00 and 2024-06-05 23:59"
- "What emails did I get on November 5th, 2025?"

The AI should:
1. Extract the date/time from your question
2. Convert to ISO format with UTC (Z suffix)
3. Call your custom function
4. Present the summary

## Debugging Tips

### If the tool isn't being called:

**Check the prompt/instructions:**
Make sure your agent's system prompt mentions the tool:
```
You have access to an email summarization tool. When the user asks about their emails 
from a specific date or time range, use the summarize_emails function with proper ISO 
timestamps in UTC timezone (ending with Z).
```

**Check the ngrok tunnel:**
```bash
# In browser, visit:
http://127.0.0.1:4040/inspect/http
```
This shows all incoming requests. If nothing appears when you ask the agent, it's not calling the tool.

**Test the API directly:**
```bash
curl -X POST https://hellen-sarraceniaceous-adelina.ngrok-free.dev/tool/read_emails \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "summarize_emails",
    "absolute_time_range": {
      "start_iso": "2024-06-05T00:00:00Z",
      "end_iso": "2024-06-05T23:59:59Z"
    }
  }'
```

### Common Issues:

1. **ngrok expired**: Free ngrok sessions expire. Restart with `./start_ngrok.sh`
2. **Wrong date format**: Must be ISO with Z (UTC), not local time
3. **AI didn't understand**: Be explicit: "Use the email tool to check June 5th 2024"
4. **CORS issues**: Add CORS headers if needed (see below)

## Alternative: Simpler Custom Tool (No Code Required)

If the JavaScript approach is complex, try using **HTTP Action** instead:

1. **Tools** → **Add** → **HTTP Action**
2. **URL**: `https://hellen-sarraceniaceous-adelina.ngrok-free.dev/tool/read_emails`
3. **Method**: POST
4. **Headers**: `Content-Type: application/json`
5. **Body Template**:
```json
{
  "intent": "summarize_emails",
  "absolute_time_range": {
    "start_iso": "{{start_iso}}",
    "end_iso": "{{end_iso}}"
  }
}
```
6. **Parameters**: Define `start_iso` and `end_iso` as string parameters

This way the Agent Builder handles the HTTP call for you!

---

## Testing MCP Endpoints

You can test the MCP protocol directly:

```bash
# Initialize connection
curl -X POST https://hellen-sarraceniaceous-adelina.ngrok-free.dev/mcp/v1/initialize \
  -H "Content-Type: application/json" \
  -d '{"protocolVersion":"2024-11-05","clientInfo":{"name":"test-client","version":"1.0"}}'

# List available tools
curl -X POST https://hellen-sarraceniaceous-adelina.ngrok-free.dev/mcp/v1/tools/list \
  -H "Content-Type: application/json" \
  -d '{}'

# Call the summarize_emails tool
curl -X POST https://hellen-sarraceniaceous-adelina.ngrok-free.dev/mcp/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "summarize_emails",
    "arguments": {
      "start_iso": "2025-11-09T00:00:00Z",
      "end_iso": "2025-11-09T23:59:59Z"
    }
  }'
```

## Summary

Your Flask server now supports **both** integration methods:

1. **MCP Protocol** (recommended): Register `https://hellen-sarraceniaceous-adelina.ngrok-free.dev` as MCP server
2. **Direct HTTP**: Use `/tool/read_emails` endpoint with custom action configuration

Choose the method that works with your Agent Builder interface!
