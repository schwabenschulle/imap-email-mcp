#!/bin/bash
# Start ngrok tunnel for Flask Email MCP Server with custom domain

PORT=5001
DOMAIN="frankimap.ngrok.dev"

echo "🚀 Starting ngrok tunnel for port $PORT with custom domain..."
echo "   Domain: https://$DOMAIN"
echo ""
echo "Make sure your Flask server is running in another terminal:"
echo "  cd /Users/frank/projects/ai-agent/flask-email-mcp"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
echo "Starting ngrok..."
echo "═══════════════════════════════════════════════════════════"

# Start ngrok with custom domain (paid feature removes browser warning automatically)
ngrok http $PORT --domain=$DOMAIN
