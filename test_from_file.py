#!/usr/bin/env python3
"""
Test script for Flask Email MCP Server
Reads input from test_input.json file
"""
import requests
import json
import sys
import os

# Server URL
SERVER_URL = "http://localhost:5001"

def test_from_json_file(json_file="test_input.json"):
    """Test the read_emails tool using JSON file input."""
    
    if not os.path.exists(json_file):
        print(f"[ERROR] JSON file not found: {json_file}")
        print(f"\nCreate a file named '{json_file}' with this format:")
        print(json.dumps({
            "intent": "summarize_emails",
            "absolute_time_range": {
                "start_iso": "2024-06-05T00:00:00Z",
                "end_iso": "2024-06-05T23:59:59Z"
            }
        }, indent=2))
        sys.exit(1)
    
    try:
        with open(json_file, 'r') as f:
            payload = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read JSON file: {e}")
        sys.exit(1)
    
    print("=" * 60)
    print("Testing Flask Email MCP Server")
    print("=" * 60)
    print(f"\nReading input from: {json_file}")
    print(f"Sending request to: {SERVER_URL}/tool/read_emails")
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    print("\n" + "=" * 60)
    
    try:
        response = requests.post(
            f"{SERVER_URL}/tool/read_emails",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print("\nResponse:")
        print(json.dumps(response.json(), indent=2))
        
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to server.")
        print("Make sure the Flask server is running: python app.py")
    except Exception as e:
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    # Check if custom JSON file provided as argument
    json_file = sys.argv[1] if len(sys.argv) > 1 else "test_input.json"
    test_from_json_file(json_file)
