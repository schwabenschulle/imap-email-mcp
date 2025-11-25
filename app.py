#!/usr/bin/env python3
"""
Flask-based MCP Server with Email Reading Tool
Accepts JSON input with intent and absolute_time_range for summarizing emails.
"""
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timezone
import imaplib
import ssl
import email
from email.header import decode_header
from zoneinfo import ZoneInfo
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for OpenAI Agent Builder
CORS(app, resources={
    r"/*": {
        "origins": ["https://platform.openai.com", "https://chat.openai.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Middleware to bypass ngrok anti-abuse page
@app.before_request
def add_ngrok_skip_header_to_request():
    """Add header to bypass ngrok browser warning page for incoming requests"""
    # This helps ngrok recognize the request as non-browser traffic
    pass

@app.after_request
def add_ngrok_skip_header_to_response(response):
    """Add header to bypass ngrok browser warning page in responses"""
    response.headers['ngrok-skip-browser-warning'] = 'true'
    response.headers['User-Agent'] = 'OpenAI-MCP-Client'
    return response

# Configure OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Email configuration
IMAP_HOST = os.getenv("IMAP_HOST", "imap.strato.de")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")

if not IMAP_USER or not IMAP_PASS:
    print("[ERROR] Missing IMAP_USER or IMAP_PASS in .env file", file=sys.stderr)
    sys.exit(1)

if not os.getenv("OPENAI_API_KEY"):
    print("[ERROR] Missing OPENAI_API_KEY in .env file", file=sys.stderr)
    sys.exit(1)


def decode_email_header(header_value):
    """Decode email header (handles encoding)."""
    if not header_value:
        return ""
    
    decoded_parts = decode_header(header_value)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(encoding or "utf-8", errors="ignore"))
        else:
            result.append(str(part))
    return " ".join(result)


def fetch_emails_in_timerange(start_iso, end_iso):
    """
    Fetch emails from IMAP within the given ISO timestamp range.
    
    Args:
        start_iso: Start time in ISO format (e.g., "2024-06-05T00:00:00Z")
        end_iso: End time in ISO format (e.g., "2024-06-05T23:59:59Z")
    
    Returns:
        List of email dictionaries with from, subject, date, body preview
    """
    try:
        # Parse ISO timestamps
        start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
        
        print(f"[INFO] Fetching emails from {start_dt} to {end_dt}", file=sys.stderr)
        
        # Convert to IMAP search format (DD-Mon-YYYY)
        since_str = start_dt.strftime("%d-%b-%Y")
        before_str = (end_dt).strftime("%d-%b-%Y")
        
        # Connect to IMAP
        conn = imaplib.IMAP4_SSL(IMAP_HOST, port=993, ssl_context=ssl.create_default_context())
        conn.login(IMAP_USER, IMAP_PASS)
        
        res, _ = conn.select("INBOX")
        if res != "OK":
            conn.logout()
            return {"error": "Could not open INBOX"}
        
        # Search for emails in date range
        search_criteria = f'(SINCE "{since_str}")'
        print(f"[DEBUG] IMAP search: {search_criteria}", file=sys.stderr)
        
        typ, data = conn.search(None, search_criteria)
        if typ != "OK":
            conn.logout()
            return {"error": "IMAP search failed"}
        
        ids = data[0].split() if data and data[0] else []
        print(f"[INFO] Found {len(ids)} emails", file=sys.stderr)
        
        if not ids:
            conn.logout()
            return []
        
        # Fetch email details
        emails = []
        tz_berlin = ZoneInfo("Europe/Berlin")
        
        for msg_id in ids:
            try:
                typ, msg_data = conn.fetch(msg_id, "(RFC822)")
                if typ != "OK" or not msg_data:
                    continue
                
                # Parse email
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Extract headers
                raw_from = msg.get("From", "(unknown sender)")
                raw_subject = msg.get("Subject", "(no subject)")
                raw_date = msg.get("Date", "")
                
                # Decode subject
                subject = decode_email_header(raw_subject)
                from_addr = decode_email_header(raw_from)
                
                # Parse date
                email_dt = None
                utc_timestamp = None
                local_time = None
                
                if raw_date:
                    try:
                        from email.utils import parsedate_to_datetime
                        email_dt = parsedate_to_datetime(raw_date)
                        utc_timestamp = email_dt.timestamp()
                        local_time = email_dt.astimezone(tz_berlin).isoformat()
                        
                        # Filter by actual timestamp (not just date)
                        if email_dt < start_dt or email_dt > end_dt:
                            continue
                            
                    except Exception as e:
                        print(f"[WARN] Could not parse date '{raw_date}': {e}", file=sys.stderr)
                
                # Extract body preview
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(errors="ignore")[:500]
                                    break
                            except:
                                pass
                else:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")[:500]
                    except:
                        pass
                
                emails.append({
                    "from": from_addr,
                    "subject": subject,
                    "date": raw_date,
                    "local_time": local_time,
                    "utc_timestamp": utc_timestamp,
                    "body_preview": body.strip()[:200] if body else "(no body)"
                })
                
            except Exception as e:
                print(f"[WARN] Error processing email {msg_id}: {e}", file=sys.stderr)
                continue
        
        conn.logout()
        print(f"[INFO] Returning {len(emails)} emails after filtering", file=sys.stderr)
        return emails
        
    except Exception as e:
        print(f"[ERROR] IMAP error: {e}", file=sys.stderr)
        return {"error": str(e)}


def summarize_emails_with_ai(emails):
    """
    Use OpenAI to summarize a list of emails.
    
    Args:
        emails: List of email dictionaries
    
    Returns:
        AI-generated summary string
    """
    if not emails:
        return "No emails found in the specified time range."
    
    # Build context for AI
    email_text = []
    for i, email_obj in enumerate(emails, 1):
        email_text.append(f"""
Email {i}:
From: {email_obj.get('from', 'Unknown')}
Subject: {email_obj.get('subject', 'No subject')}
Date: {email_obj.get('local_time', 'Unknown date')}
Preview: {email_obj.get('body_preview', 'No preview')}
---
""")
    
    context = "\n".join(email_text)
    
    # Call OpenAI
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an email summarization assistant. Provide a concise summary of the emails, highlighting key senders, topics, and action items."},
                {"role": "user", "content": f"Please summarize these {len(emails)} emails:\n\n{context}"}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        summary = response.choices[0].message.content
        return summary
        
    except Exception as e:
        print(f"[ERROR] OpenAI error: {e}", file=sys.stderr)
        return f"Error generating summary: {e}"


@app.route("/", methods=["GET", "POST"])
def home():
    """Health check endpoint and MCP discovery."""
    if request.method == "POST":
        # If it's a POST request, treat it as MCP initialization
        return mcp_initialize()
    
    # GET request - return server info
    return jsonify({
        "service": "Flask Email MCP Server",
        "status": "running",
        "version": "1.0.0",
        "protocols": ["mcp", "openapi"],
        "mcp_endpoints": {
            "initialize": "/mcp/v1/initialize",
            "tools_list": "/mcp/v1/tools/list", 
            "tools_call": "/mcp/v1/tools/call"
        },
        "openapi_schema": "/openapi.json",
        "endpoints": [
            {"path": "/tools", "method": "GET", "description": "OpenAI tool discovery (returns tool list)"},
            {"path": "/tool/read_emails", "method": "POST", "description": "Read and summarize emails in time range (REST API)"},
            {"path": "/openapi.json", "method": "GET", "description": "OpenAPI schema for OpenAI integration"},
            {"path": "/.well-known/ai-plugin.json", "method": "GET", "description": "AI plugin manifest"},
            {"path": "/mcp/v1/initialize", "method": "POST", "description": "MCP protocol initialization"},
            {"path": "/mcp/v1/tools/list", "method": "POST", "description": "MCP protocol tools discovery"},
            {"path": "/mcp/v1/tools/call", "method": "POST", "description": "MCP protocol tool execution"}
        ]
    })


@app.route("/tools", methods=["GET"])
def openai_tools():
    """OpenAI tool discovery endpoint."""
    return jsonify({
        "tools": [
            {
                "name": "read_emails",
                "description": "Read and summarize emails in time range.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "Must be 'summarize_emails'"
                        },
                        "absolute_time_range": {
                            "type": "object",
                            "properties": {
                                "start_iso": {
                                    "type": "string",
                                    "description": "Start time in ISO 8601 format (e.g., '2025-11-09T00:00:00Z')"
                                },
                                "end_iso": {
                                    "type": "string",
                                    "description": "End time in ISO 8601 format (e.g., '2025-11-09T23:59:59Z')"
                                }
                            },
                            "required": ["start_iso", "end_iso"]
                        }
                    },
                    "required": ["intent", "absolute_time_range"]
                }
            }
        ]
    })


@app.route("/openapi.json", methods=["GET"])
def openapi_schema():
    """OpenAPI schema for OpenAI Custom GPT Actions."""
    schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "Email Summarization API",
            "description": "Read and summarize emails from IMAP mailbox in specified time range",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": request.url_root.rstrip('/'),
                "description": "Flask Email MCP Server"
            }
        ],
        "paths": {
            "/tool/read_emails": {
                "post": {
                    "operationId": "summarize_emails",
                    "summary": "Read and summarize emails in time range",
                    "description": "Fetches emails from IMAP mailbox within specified ISO timestamp range and generates AI summary",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["intent", "absolute_time_range"],
                                    "properties": {
                                        "intent": {
                                            "type": "string",
                                            "enum": ["summarize_emails"],
                                            "description": "Action to perform"
                                        },
                                        "absolute_time_range": {
                                            "type": "object",
                                            "required": ["start_iso", "end_iso"],
                                            "properties": {
                                                "start_iso": {
                                                    "type": "string",
                                                    "format": "date-time",
                                                    "description": "Start time in ISO format (UTC with Z suffix)",
                                                    "example": "2024-06-05T00:00:00Z"
                                                },
                                                "end_iso": {
                                                    "type": "string",
                                                    "format": "date-time",
                                                    "description": "End time in ISO format (UTC with Z suffix)",
                                                    "example": "2024-06-05T23:59:59Z"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Email summary response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "intent": {"type": "string"},
                                            "time_range": {"type": "object"},
                                            "email_count": {"type": "integer"},
                                            "emails": {"type": "array"},
                                            "summary": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {"description": "Bad request"},
                        "500": {"description": "Server error"}
                    }
                }
            }
        }
    }
    return jsonify(schema)


@app.route("/.well-known/ai-plugin.json", methods=["GET"])
def ai_plugin():
    """AI plugin manifest for OpenAI."""
    manifest = {
        "schema_version": "v1",
        "name_for_human": "Email Summarizer",
        "name_for_model": "email_summarizer",
        "description_for_human": "Read and summarize emails from your mailbox in a specified time range.",
        "description_for_model": "Fetches emails from an IMAP mailbox within a specified ISO timestamp range (UTC with Z suffix) and generates an AI-powered summary. Use this when the user asks about emails from a specific date or time period.",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": f"{request.url_root.rstrip('/')}/openapi.json"
        },
        "logo_url": f"{request.url_root.rstrip('/')}/logo.png",
        "contact_email": "frank@family-schulze.de",
        "legal_info_url": f"{request.url_root.rstrip('/')}"
    }
    return jsonify(manifest)


@app.route("/tool/read_emails", methods=["POST"])
def read_emails_tool():
    """
    MCP Tool: Read and summarize emails
    
    Expected JSON input:
    {
        "intent": "summarize_emails",
        "absolute_time_range": {
            "start_iso": "2024-06-05T00:00:00Z",
            "end_iso": "2024-06-05T23:59:59Z"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract parameters
        intent = data.get("intent")
        time_range = data.get("absolute_time_range", {})
        
        if intent != "summarize_emails":
            return jsonify({"error": f"Unknown intent: {intent}"}), 400
        
        start_iso = time_range.get("start_iso")
        end_iso = time_range.get("end_iso")
        
        if not start_iso or not end_iso:
            return jsonify({
                "error": "Missing start_iso or end_iso in absolute_time_range"
            }), 400
        
        print(f"[INFO] Processing request: {intent} from {start_iso} to {end_iso}", file=sys.stderr)
        
        # Fetch emails
        emails = fetch_emails_in_timerange(start_iso, end_iso)
        
        if isinstance(emails, dict) and "error" in emails:
            return jsonify(emails), 500
        
        # Generate summary
        summary = summarize_emails_with_ai(emails)
        
        # Return response
        return jsonify({
            "intent": intent,
            "time_range": {
                "start": start_iso,
                "end": end_iso
            },
            "email_count": len(emails),
            "emails": emails,
            "summary": summary
        })
        
    except Exception as e:
        print(f"[ERROR] Request failed: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


# ============================================================================
# MCP Protocol HTTP Endpoints
# ============================================================================

@app.route('/mcp/v1/initialize', methods=['POST'])
def mcp_initialize():
    """MCP protocol initialization endpoint"""
    try:
        data = request.get_json() or {}
        client_info = data.get('clientInfo', {})
        protocol_version = data.get('protocolVersion', '2024-11-05')
        
        print(f"[MCP] Initialize request from {client_info.get('name', 'unknown')}", file=sys.stderr)
        
        return jsonify({
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "email-summarization-mcp",
                "version": "1.0.0"
            }
        })
    except Exception as e:
        print(f"[ERROR] MCP initialize failed: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


@app.route('/mcp/v1/tools/list', methods=['POST'])
def mcp_tools_list():
    """MCP protocol tools list endpoint - OpenAI Agent Builder format"""
    try:
        print("[MCP] Tools list request", file=sys.stderr)
        
        # Return in OpenAI Agent Builder format (not standard MCP format)
        return jsonify({
            "tools": [
                {
                    "name": "read_emails",
                    "description": "Read and summarize emails in time range.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "intent": {
                                "type": "string",
                                "description": "Must be 'summarize_emails'"
                            },
                            "absolute_time_range": {
                                "type": "object",
                                "properties": {
                                    "start_iso": {
                                        "type": "string",
                                        "description": "Start time in ISO 8601 format (e.g., '2025-11-09T00:00:00Z')"
                                    },
                                    "end_iso": {
                                        "type": "string",
                                        "description": "End time in ISO 8601 format (e.g., '2025-11-09T23:59:59Z')"
                                    }
                                },
                                "required": ["start_iso", "end_iso"]
                            }
                        },
                        "required": ["intent", "absolute_time_range"]
                    }
                }
            ]
        })
    except Exception as e:
        print(f"[ERROR] MCP tools list failed: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


@app.route('/mcp/v1/tools/call', methods=['POST'])
def mcp_tools_call():
    """MCP protocol tool call endpoint"""
    try:
        data = request.get_json()
        tool_name = data.get('name')
        arguments = data.get('arguments', {})
        
        print(f"[MCP] Tool call: {tool_name} with args {arguments}", file=sys.stderr)
        
        if tool_name != "read_emails":
            return jsonify({
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"Unknown tool: {tool_name}"
                    }
                ]
            }), 400
        
        # Extract parameters from arguments
        # Arguments should contain: {"intent": "summarize_emails", "absolute_time_range": {...}}
        intent = arguments.get('intent')
        time_range = arguments.get('absolute_time_range', {})
        start_iso = time_range.get('start_iso')
        end_iso = time_range.get('end_iso')
        
        if not start_iso or not end_iso:
            return jsonify({
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Missing required parameters: absolute_time_range with start_iso and end_iso"
                    }
                ]
            }), 400
        
        # Fetch and summarize emails
        emails = fetch_emails_in_timerange(start_iso, end_iso)
        summary = summarize_emails_with_ai(emails)
        
        # Format response
        email_list = "\n".join([
            f"- {email['subject']} (from {email['from']}, {email['date']})"
            for email in emails
        ])
        
        result_text = f"""Email Summary for {start_iso} to {end_iso}

Found {len(emails)} email(s)

Emails:
{email_list if emails else '(none)'}

Summary:
{summary}"""
        
        return jsonify({
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        })
        
    except Exception as e:
        print(f"[ERROR] MCP tool call failed: {e}", file=sys.stderr)
        return jsonify({
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": f"Error: {str(e)}"
                }
            ]
        }), 500


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    
    print(f"[INFO] Starting Flask Email MCP Server on {host}:{port}", file=sys.stderr)
    print(f"[INFO] IMAP: {IMAP_USER}@{IMAP_HOST}", file=sys.stderr)
    
    app.run(host=host, port=port, debug=True)
