# FastMCP Email Server Setup

## Why FastMCP?

FastMCP is the **production-ready framework** for building MCP servers that work with OpenAI and other LLM clients. Unlike basic Flask implementations:

✅ **Native MCP Protocol** - Full compliance with Model Context Protocol spec  
✅ **HTTP/SSE Transport** - Works with OpenAI ChatGPT and Agent Builder  
✅ **Simple Decorator API** - Just use `@mcp.tool()` on your functions  
✅ **Built-in Auth Support** - OAuth, API keys, JWT, etc.  
✅ **Automatic Schema Generation** - From Python type hints  
✅ **Production Ready** - Used by 5.4k+ projects  

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/frank/projects/ai-agent/flask-email-mcp
source venv/bin/activate
pip install -r requirements-fastmcp.txt
```

### 2. Configure Environment

Make sure your `.env` file has:
```env
OPENAI_API_KEY=sk-...
IMAP_HOST=imap.strato.de
IMAP_USER=frank@family-schulze.de
IMAP_PASS=your_password
```

### 3. Run the Server

**Option A: Using FastMCP CLI (Recommended)**
```bash
fastmcp run fastmcp_server.py --transport sse --host 0.0.0.0 --port 5001
```

**Option B: Using the script**
```bash
./run_fastmcp.sh
```

**Option C: Direct Python**
```bash
python fastmcp_server.py
```

### 4. Start ngrok (in another terminal)

```bash
./start_ngrok.sh
```

Your server will be available at: `https://frankimap.ngrok.dev`

## Connecting to OpenAI

### Method 1: ChatGPT (Recommended)

1. Go to https://chatgpt.com
2. Open Settings → Integrations
3. Click "Add MCP Server"
4. **Server Type**: SSE
5. **URL**: `https://frankimap.ngrok.dev/sse`
6. **Name**: Email Summarizer
7. Click "Connect"

### Method 2: OpenAI Agent Builder (Actions)

FastMCP automatically provides an OpenAPI schema at `/openapi.json`:

1. Go to https://platform.openai.com/playground
2. Create/Edit your Assistant
3. Add Action → Import from URL
4. URL: `https://frankimap.ngrok.dev/openapi.json`
5. Save

## How It Works

### The FastMCP Server

```python
from fastmcp import FastMCP

mcp = FastMCP("Email Summarizer 📧")

@mcp.tool()
def summarize_emails(start_iso: str, end_iso: str) -> dict:
    """Fetch and summarize emails from a specified time range."""
    # Your email logic here
    return {"summary": "...", "emails": [...]}

# Run with SSE transport for OpenAI
mcp.run(transport="sse", host="0.0.0.0", port=5001)
```

That's it! FastMCP handles:
- ✅ MCP protocol implementation
- ✅ Schema generation from type hints
- ✅ Transport layer (SSE/HTTP/stdio)
- ✅ Error handling
- ✅ Request/response validation

## Testing Your Server

### Test with curl

```bash
# Test health endpoint
curl https://frankimap.ngrok.dev/sse

# Test tool (if OpenAPI endpoint is available)
curl -X POST https://frankimap.ngrok.dev/tool/summarize_emails \
  -H "Content-Type: application/json" \
  -d '{
    "start_iso": "2024-06-05T00:00:00Z",
    "end_iso": "2024-06-05T23:59:59Z"
  }'
```

### Test with Python Client

```python
from fastmcp import Client

async def test():
    async with Client("https://frankimap.ngrok.dev/sse") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Tools: {tools}")
        
        # Call the summarize_emails tool
        result = await client.call_tool(
            "summarize_emails",
            {
                "start_iso": "2024-06-05T00:00:00Z",
                "end_iso": "2024-06-05T23:59:59Z"
            }
        )
        print(f"Result: {result.content[0].text}")

import asyncio
asyncio.run(test())
```

## Available Endpoints

When running with SSE transport:

- **SSE Endpoint**: `https://frankimap.ngrok.dev/sse` - MCP over Server-Sent Events
- **OpenAPI Schema**: `https://frankimap.ngrok.dev/openapi.json` - For OpenAI Actions
- **Health Check**: `https://frankimap.ngrok.dev/` - Server status

## Advantages over Flask Approach

| Feature | Flask (Custom) | FastMCP |
|---------|---------------|---------|
| MCP Protocol | ❌ Manual implementation | ✅ Built-in |
| Schema Generation | ❌ Manual JSON | ✅ Auto from type hints |
| Multiple Transports | ❌ HTTP only | ✅ SSE/HTTP/stdio |
| OpenAI Compatible | ⚠️ Needs workarounds | ✅ Native support |
| Auth Support | ❌ DIY | ✅ OAuth, JWT, etc. |
| Documentation | ❌ DIY | ✅ Auto-generated |
| Community | ❌ None | ✅ 20.6k stars |

## Troubleshooting

### "Connection refused"
- Make sure the server is running: `fastmcp run fastmcp_server.py --transport sse --port 5001`
- Check if port 5001 is available: `lsof -i :5001`

### "Tool not found" in OpenAI
- Verify the server is accessible: `curl https://frankimap.ngrok.dev/sse`
- Check ngrok is running: visit `http://127.0.0.1:4040`
- Make sure you're using the SSE endpoint, not the root URL

### "Import fastmcp could not be resolved"
- Install FastMCP: `pip install fastmcp`
- Make sure virtual environment is activated
- Check Python version: `python --version` (need 3.10+)

### IMAP errors
- Verify credentials in `.env`
- Test IMAP directly: `python -c "import imaplib; m=imaplib.IMAP4_SSL('imap.strato.de'); m.login('user', 'pass')"`

## Next Steps

1. **Test locally** with the FastMCP client
2. **Connect to ChatGPT** using the SSE endpoint
3. **Add authentication** (see [FastMCP Auth Docs](https://gofastmcp.com/servers/auth))
4. **Deploy to production** (see [FastMCP Cloud](https://fastmcp.cloud/))

## Resources

- 📚 [FastMCP Documentation](https://gofastmcp.com/)
- 💬 [FastMCP Discord](https://discord.gg/uu8dJCgttd)
- 🐙 [GitHub Repository](https://github.com/jlowin/fastmcp)
- 🔧 [MCP Specification](https://modelcontextprotocol.io/)

## Migration from Flask

The FastMCP server (`fastmcp_server.py`) replaces `app.py`. Key differences:

1. **Decorator**: Use `@mcp.tool()` instead of `@app.route()`
2. **Transport**: Specify `transport="sse"` for OpenAI compatibility
3. **Schema**: Auto-generated from type hints and docstrings
4. **Protocol**: Native MCP instead of custom REST API

Your existing `.env` file and ngrok configuration work as-is!
