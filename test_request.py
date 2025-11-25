#!/usr/bin/env python3
"""
Test script for Flask Email MCP Server
Sends a sample request to the /tool/read_emails endpoint
"""
import requests
import json
from datetime import datetime, timedelta

# Server URL
SERVER_URL = "http://localhost:5001"

def test_read_emails():
    """Test the read_emails tool with a sample time range."""
    
    # Example: Get emails from June 5th, 2024
    payload = {
        "intent": "summarize_emails",
        "absolute_time_range": {
            "start_iso": "2024-06-05T00:00:00Z",
            "end_iso": "2024-06-05T23:59:59Z"
        }
    }
    
    print("=" * 60)
    print("Testing Flask Email MCP Server")
    print("=" * 60)
    print(f"\nSending request to: {SERVER_URL}/tool/read_emails")
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


def test_today():
    """Test with today's date range."""
    
    from datetime import timezone
    
    # Get today in UTC
    today_utc = datetime.now(timezone.utc)
    start = today_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    end = today_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Format as ISO with 'Z' suffix for UTC
    payload = {
        "intent": "summarize_emails",
        "absolute_time_range": {
            "start_iso": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_iso": end.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }
    
    print("=" * 60)
    print("Testing with TODAY's emails (UTC timezone)")
    print("=" * 60)
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
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "today":
        test_today()
    else:
        test_read_emails()
        print("\n\nTip: Run 'python test_request.py today' to test with today's emails")
