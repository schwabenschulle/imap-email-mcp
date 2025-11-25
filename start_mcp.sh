#!/bin/bash
# Start MCP SSE Server

cd /Users/frank/projects/ai-agent/flask-email-mcp

echo "🚀 Starting MCP SSE Email Server..."
echo ""

# Check and install dependencies if needed
echo "Checking dependencies..."
pip3 install -q python-dotenv openai fastapi uvicorn sse-starlette 2>/dev/null

echo ""
echo "Starting server on port 5001..."
echo "MCP SSE endpoint: http://localhost:5001/sse"
echo ""

python3 mcp_sse_server.py
