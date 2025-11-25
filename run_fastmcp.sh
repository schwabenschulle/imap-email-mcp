#!/bin/bash
# Run FastMCP Email Server with HTTP transport

PORT=5001
DOMAIN="frankimap.ngrok.dev"

echo "🚀 Starting FastMCP Email Server..."
echo "   Port: $PORT"
echo "   Transport: HTTP (OpenAI compatible)"
echo ""
echo "Make sure you have:"
echo "  1. Installed dependencies: pip3 install fastmcp python-dotenv openai"
echo "  2. Configured .env file with IMAP and OpenAI credentials"
echo ""
echo "Starting server..."
echo "═══════════════════════════════════════════════════════════"

# Run directly with Python (HTTP transport)
python3 fastmcp_server.py
