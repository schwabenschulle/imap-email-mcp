#!/bin/bash
# Test the send_email tool with curl

DOMAIN="https://frankimap.ngrok.dev"

echo "📧 Testing send_email tool"
echo "=========================="
echo ""

# Example 1: Simple email
echo "1️⃣  Simple email to one recipient"
curl -X POST "$DOMAIN/sse" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "send_email",
      "arguments": {
        "to": ["recipient@example.com"],
        "subject": "Test Email from MCP Server",
        "body": "This is a test email sent via the MCP email server.\n\nBest regards,\nFrank"
      }
    }
  }'

echo ""
echo ""

# Example 2: Email with CC and BCC
echo "2️⃣  Email with CC and BCC"
curl -X POST "$DOMAIN/sse" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "send_email",
      "arguments": {
        "to": ["primary@example.com"],
        "cc": ["cc-recipient@example.com"],
        "bcc": ["bcc-recipient@example.com"],
        "subject": "Meeting Summary",
        "body": "Here is the summary of our meeting...",
        "body_type": "plain"
      }
    }
  }'

echo ""
echo ""

# Example 3: HTML email
echo "3️⃣  HTML email"
curl -X POST "$DOMAIN/sse" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "send_email",
      "arguments": {
        "to": ["recipient@example.com"],
        "subject": "Newsletter",
        "body": "<html><body><h1>Welcome!</h1><p>This is an <strong>HTML</strong> email.</p></body></html>",
        "body_type": "html"
      }
    }
  }'

echo ""
echo ""
echo "✅ Tests complete!"
