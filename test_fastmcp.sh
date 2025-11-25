#!/bin/bash
# Test FastMCP Email Server with curl

DOMAIN="https://frankimap.ngrok.dev"

echo "🧪 Testing FastMCP Email Server"
echo "================================"
echo ""
echo "Server: $DOMAIN"
echo ""

# Test 1: Health Check
echo "1️⃣  Testing health endpoint..."
echo "   curl $DOMAIN/"
echo ""
curl -s "$DOMAIN/" | python3 -m json.tool 2>/dev/null || curl -s "$DOMAIN/"
echo ""
echo ""

# Test 2: SSE Endpoint (MCP)
echo "2️⃣  Testing SSE endpoint (MCP)..."
echo "   curl $DOMAIN/sse"
echo ""
echo "   Note: This should return SSE stream or connection info"
curl -s -m 2 "$DOMAIN/sse" 2>&1 | head -20
echo ""
echo ""

# Test 3: OpenAPI Schema
echo "3️⃣  Testing OpenAPI schema..."
echo "   curl $DOMAIN/openapi.json"
echo ""
curl -s "$DOMAIN/openapi.json" | python3 -m json.tool 2>/dev/null | head -50
echo ""
echo "   ... (truncated)"
echo ""

# Test 4: MCP Tools List (if available)
echo "4️⃣  Testing MCP tools list..."
echo "   This may require proper MCP client headers"
echo ""

# Test 5: Sample email query (using today's date)
TODAY_START=$(date -u +"%Y-%m-%dT00:00:00Z")
TODAY_END=$(date -u +"%Y-%m-%dT23:59:59Z")

echo "5️⃣  Testing tool call (if direct HTTP is supported)..."
echo "   Time range: $TODAY_START to $TODAY_END"
echo ""
echo "   Note: FastMCP with SSE transport may not support direct HTTP tool calls"
echo "   Use MCP client or ChatGPT to call tools properly"
echo ""

echo "================================"
echo "✅ Basic tests complete!"
echo ""
echo "To fully test the MCP functionality:"
echo "  1. Use the FastMCP Python client (see FASTMCP_SETUP.md)"
echo "  2. Connect via ChatGPT Desktop (Settings → Integrations)"
echo "  3. Use OpenAI Agent Builder with the OpenAPI schema"
