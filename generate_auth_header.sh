#!/bin/bash
# Generate Basic Auth header for OpenAI Builder
# Usage: ./generate_auth_header.sh username:password

if [ -z "$1" ]; then
    echo "Usage: ./generate_auth_header.sh username:password"
    echo ""
    echo "Example:"
    echo "  ./generate_auth_header.sh frank:aibuilderpw2025"
    exit 1
fi

CREDENTIALS="$1"
ENCODED=$(echo -n "$CREDENTIALS" | base64)

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "OpenAI Builder Custom Header Configuration"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Add this custom header in OpenAI Builder:"
echo ""
echo "Header Name:  Authorization"
echo "Header Value: Basic $ENCODED"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
