# Quick Guide: Flask API + Web Agent Builder

## Current Status

✅ Flask server working: `flask-email-mcp/app.py`
✅ CORS enabled
✅ OpenAPI schema available
✅ Tested with curl - works!
✅ ngrok tunnel active

## For Web-Based OpenAI Agent Builder

The web Agent Builder **cannot use the MCP button** for your local server. Instead, try these approaches:

### Option 1: Custom GPT with Actions (ChatGPT Plus)

If you have ChatGPT Plus:

1. Go to https://chat.openai.com
2. Your name → My GPTs → Create a GPT
3. Configure tab → Actions
4. Import from URL: `https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json`

### Option 2: Ask Agent Builder to Generate Function

In Agent Builder:

1. Tools → Function
2. Click "Generate" 
3. Describe: "Call a REST API at https://hellen-sarraceniaceous-adelina.ngrok-free.dev/tool/read_emails that summarizes emails. It needs start_iso and end_iso parameters in format 2024-06-05T00:00:00Z, sent as JSON body with intent: summarize_emails and absolute_time_range object."
4. Let it auto-generate the function

### Option 3: Direct Function Definition

If Agent Builder has a function editor, paste this:

```typescript
interface EmailSummaryParams {
  start_iso: string; // ISO format: "2024-06-05T00:00:00Z"
  end_iso: string;   // ISO format: "2024-06-05T23:59:59Z"
}

// This function calls your Flask API
// Agent Builder will handle the HTTP call automatically
```

## What about the MCP Server?

The **MCP stdio server** (`email-mcp-server`) is useful if:
- You use **Claude Desktop** (has native MCP support)
- You use **OpenAI Desktop app** (when released)
- You're building a **CLI tool** that needs MCP

For **web-based Agent Builder**, stick with the Flask API approach!

## Next Steps

1. Keep Flask + ngrok running
2. Try the "Generate function" approach in Agent Builder
3. Describe your API endpoint and let the AI figure out how to call it

The Agent Builder is smart enough to generate HTTP calls from descriptions. You don't need to write JavaScript code yourself.

## Testing

Once added, test with:
- "Check my emails from November 9th, 2025"
- "Summarize emails from yesterday"

Watch ngrok inspector (http://127.0.0.1:4040) to see if calls come through!
