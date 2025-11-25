#!/bin/bash
# Start Flask Email MCP Server

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Start server
echo "Starting Flask Email MCP Server..."
python app.py
