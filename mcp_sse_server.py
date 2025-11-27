#!/usr/bin/env python3
"""
FastMCP Email Server with proper SSE support for OpenAI Responses API
"""
import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import imaplib
import smtplib
import ssl
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Load environment variables
load_dotenv()

# Configure OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Email configuration
IMAP_HOST = os.getenv("IMAP_HOST", "imap.strato.de")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.strato.de")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))  # SSL port
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Frank Schulze")

# Authentication configuration
MCP_API_KEY = os.getenv("MCP_API_KEY")

if not IMAP_USER or not IMAP_PASS:
    print("[ERROR] Missing IMAP_USER or IMAP_PASS in .env file", file=sys.stderr)
    sys.exit(1)

if not os.getenv("OPENAI_API_KEY"):
    print("[ERROR] Missing OPENAI_API_KEY in .env file", file=sys.stderr)
    sys.exit(1)

if MCP_API_KEY:
    print("[INFO] MCP API Key authentication enabled", flush=True)
else:
    print("[WARNING] MCP_API_KEY not set - authentication disabled", flush=True)

# Create FastAPI app
app = FastAPI(title="Email Summarizer MCP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(request: Request) -> bool:
    """Verify API key from Authorization header"""
    if not MCP_API_KEY:
        # If no API key is configured, allow all requests
        return True
    
    auth_header = request.headers.get("Authorization", "")
    
    # Support both "Bearer <token>" and raw token
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif auth_header.startswith("bearer "):
        token = auth_header[7:]
    else:
        token = auth_header
    
    return token == MCP_API_KEY


def fetch_emails_from_imap(start_iso: str, end_iso: str) -> list:
    """Fetch emails from IMAP server within the specified time range."""
    try:
        start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
        
        ssl_context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=ssl_context)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("INBOX")
        
        search_date = start_dt.strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{search_date}")')
        
        if status != "OK":
            return []
        
        email_ids = messages[0].split()
        emails = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue
            
            msg = email.message_from_bytes(msg_data[0][1])
            date_str = msg.get("Date", "")
            
            try:
                email_date = email.utils.parsedate_to_datetime(date_str)
                if email_date.tzinfo is None:
                    email_date = email_date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
                
                if not (start_dt <= email_date <= end_dt):
                    continue
                
                subject = ""
                if msg.get("Subject"):
                    decoded = decode_header(msg["Subject"])[0]
                    if isinstance(decoded[0], bytes):
                        subject = decoded[0].decode(decoded[1] or "utf-8", errors="ignore")
                    else:
                        subject = decoded[0]
                
                from_header = msg.get("From", "")
                
                body_preview = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body_preview = part.get_payload(decode=True).decode("utf-8", errors="ignore")[:200]
                                break
                            except:
                                pass
                else:
                    try:
                        body_preview = msg.get_payload(decode=True).decode("utf-8", errors="ignore")[:200]
                    except:
                        pass
                
                emails.append({
                    "from": from_header,
                    "subject": subject,
                    "date": date_str,
                    "local_time": email_date.isoformat(),
                    "utc_timestamp": email_date.timestamp(),
                    "body_preview": body_preview
                })
            
            except Exception as e:
                print(f"[WARNING] Error parsing email: {e}", file=sys.stderr)
                continue
        
        mail.close()
        mail.logout()
        return emails
    
    except Exception as e:
        print(f"[ERROR] IMAP error: {e}", file=sys.stderr)
        raise


def generate_summary(emails: list) -> str:
    """Generate AI summary of emails using OpenAI."""
    if not emails:
        return "No emails found in the specified time range."
    
    try:
        email_text = "\n\n---\n\n".join([
            f"From: {e['from']}\nSubject: {e['subject']}\nDate: {e['date']}\n\n{e['body_preview']}"
            for e in emails
        ])
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes emails. Provide a concise summary of the emails below, highlighting key points, senders, and any action items."
                },
                {
                    "role": "user",
                    "content": f"Please summarize these {len(emails)} emails:\n\n{email_text}"
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"[ERROR] OpenAI error: {e}", file=sys.stderr)
        return f"Error generating summary: {e}"


def summarize_emails(start_iso: str, end_iso: str) -> Dict[str, Any]:
    """Main tool function for email summarization."""
    try:
        emails = fetch_emails_from_imap(start_iso, end_iso)
        summary = generate_summary(emails)
        
        return {
            "time_range": {"start": start_iso, "end": end_iso},
            "email_count": len(emails),
            "emails": emails,
            "summary": summary
        }
    except Exception as e:
        return {
            "error": str(e),
            "time_range": {"start": start_iso, "end": end_iso},
            "email_count": 0,
            "emails": [],
            "summary": f"Error: {e}"
        }


def read_emails(start_iso: str, end_iso: str) -> Dict[str, Any]:
    """Read and return full email content without AI summarization."""
    try:
        emails = fetch_emails_from_imap(start_iso, end_iso)
        
        return {
            "time_range": {"start": start_iso, "end": end_iso},
            "email_count": len(emails),
            "emails": emails
        }
    except Exception as e:
        return {
            "error": str(e),
            "time_range": {"start": start_iso, "end": end_iso},
            "email_count": 0,
            "emails": []
        }


def send_email(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    body_type: str = "plain"
) -> Dict[str, Any]:
    """
    Send an email via SMTP.
    
    Args:
        to: List of recipient email addresses
        subject: Email subject line
        body: Email body content
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        body_type: Email body type - "plain" or "html"
    
    Returns:
        Dictionary with send status and details
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{EMAIL_FROM_NAME} <{IMAP_USER}>"
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = ', '.join(cc)
        
        # Add body
        msg.attach(MIMEText(body, body_type))
        
        # Combine all recipients
        all_recipients = to.copy()
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)
        
        # Send via SMTP with SSL
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(IMAP_USER, IMAP_PASS)
            server.sendmail(IMAP_USER, all_recipients, msg.as_string())
        
        print(f"[EMAIL SENT] To: {to}, Subject: {subject}", flush=True)
        
        return {
            "status": "success",
            "message": "Email sent successfully",
            "recipients": {
                "to": to,
                "cc": cc or [],
                "bcc": bcc or []
            },
            "subject": subject,
            "sent_at": datetime.now(ZoneInfo("Europe/Berlin")).isoformat()
        }
    
    except Exception as e:
        print(f"[EMAIL ERROR] {e}", file=sys.stderr, flush=True)
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to send email: {e}"
        }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "FastMCP Email Server",
        "status": "running",
        "version": "1.0.0",
        "mcp_sse_endpoint": "/sse",
        "openapi_schema": "/openapi.json",
        "rest_tool": "/tool/summarize_emails"
    }


@app.get("/sse")
@app.post("/sse")
async def mcp_sse_endpoint(request: Request):
    """MCP SSE endpoint for OpenAI Responses API"""
    # Verify API key authentication
    if not verify_api_key(request):
        print("[AUTH FAILED] Invalid or missing API key", flush=True)
        return JSONResponse(
            status_code=401,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Unauthorized: Invalid or missing API key"
                }
            }
        )
    
    # Handle GET request (SSE connection info)
    if request.method == "GET":
        return {
            "protocol": "MCP over HTTP",
            "version": "2024-11-05",
            "server": "email-summarizer",
            "status": "ready",
            "note": "Send POST requests with JSON-RPC 2.0 format"
        }
    
    # Handle POST request (MCP protocol)
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        msg_id = body.get("id", 1)
        
        # Log the incoming request
        print(f"[MCP REQUEST] method={method}, params={params}", flush=True)
        
        # Handle MCP protocol methods
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "email-summarizer",
                        "version": "1.0.0"
                    }
                }
            }
            return JSONResponse(content=response)
        
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "summarize_emails",
                            "description": "Fetch and summarize emails from a specified time range. Use this when the user asks about emails from a specific date or time period. Always provide ISO 8601 timestamps in UTC with Z suffix.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "start_iso": {
                                        "type": "string",
                                        "format": "date-time",
                                        "description": "Start time in ISO 8601 format with Z suffix (e.g., '2024-06-05T00:00:00Z')"
                                    },
                                    "end_iso": {
                                        "type": "string",
                                        "format": "date-time",
                                        "description": "End time in ISO 8601 format with Z suffix (e.g., '2024-06-05T23:59:59Z')"
                                    }
                                },
                                "required": ["start_iso", "end_iso"]
                            }
                        },
                        {
                            "name": "read_emails",
                            "description": "Fetch and return full email content from a specified time range without AI summarization. Use this when the user wants to see the complete emails. Always provide ISO 8601 timestamps in UTC with Z suffix.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "start_iso": {
                                        "type": "string",
                                        "format": "date-time",
                                        "description": "Start time in ISO 8601 format with Z suffix (e.g., '2024-06-05T00:00:00Z')"
                                    },
                                    "end_iso": {
                                        "type": "string",
                                        "format": "date-time",
                                        "description": "End time in ISO 8601 format with Z suffix (e.g., '2024-06-05T23:59:59Z')"
                                    }
                                },
                                "required": ["start_iso", "end_iso"]
                            }
                        },
                        {
                            "name": "send_email",
                            "description": "Send an email to one or more recipients. Use this when the user wants to compose and send an email. Supports plain text or HTML content, CC and BCC recipients.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "to": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of recipient email addresses (e.g., ['user@example.com', 'another@example.com'])"
                                    },
                                    "subject": {
                                        "type": "string",
                                        "description": "Email subject line"
                                    },
                                    "body": {
                                        "type": "string",
                                        "description": "Email body content (plain text or HTML)"
                                    },
                                    "cc": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Optional list of CC recipients"
                                    },
                                    "bcc": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Optional list of BCC recipients"
                                    },
                                    "body_type": {
                                        "type": "string",
                                        "enum": ["plain", "html"],
                                        "description": "Email body type: 'plain' for plain text (default) or 'html' for HTML content",
                                        "default": "plain"
                                    }
                                },
                                "required": ["to", "subject", "body"]
                            }
                        }
                    ]
                }
            }
            return JSONResponse(content=response)
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "summarize_emails":
                start_iso = arguments.get("start_iso")
                end_iso = arguments.get("end_iso")
                
                result = summarize_emails(start_iso, end_iso)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
                return JSONResponse(content=response)
            
            elif tool_name == "read_emails":
                start_iso = arguments.get("start_iso")
                end_iso = arguments.get("end_iso")
                
                result = read_emails(start_iso, end_iso)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
                return JSONResponse(content=response)
            
            elif tool_name == "send_email":
                to = arguments.get("to", [])
                subject = arguments.get("subject", "")
                body = arguments.get("body", "")
                cc = arguments.get("cc")
                bcc = arguments.get("bcc")
                body_type = arguments.get("body_type", "plain")
                
                result = send_email(
                    to=to,
                    subject=subject,
                    body=body,
                    cc=cc,
                    bcc=bcc,
                    body_type=body_type
                )
                
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
                return JSONResponse(content=response)
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }
                return JSONResponse(content=response, status_code=404)
        
        elif method.startswith("notifications/"):
            # Notifications don't require a response (JSON-RPC 2.0 spec)
            # Just acknowledge with 200 OK and empty response
            print(f"[MCP NOTIFICATION] {method} - acknowledged", flush=True)
            return JSONResponse(content={}, status_code=200)
        
        else:
            print(f"[MCP 404] Unknown method: {method}", flush=True)
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            return JSONResponse(content=response, status_code=404)
    
    except Exception as e:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            },
            status_code=500
        )


@app.get("/openapi.json")
async def get_openapi_schema(request: Request):
    """OpenAPI schema for compatibility"""
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Email Summarizer API",
            "description": "MCP server for email summarization. Use /sse endpoint for MCP protocol.",
            "version": "1.0.0"
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/tool/summarize_emails": {
                "post": {
                    "operationId": "summarize_emails",
                    "summary": "Summarize emails in time range",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["start_iso", "end_iso"],
                                    "properties": {
                                        "start_iso": {
                                            "type": "string",
                                            "format": "date-time",
                                            "example": "2024-06-05T00:00:00Z"
                                        },
                                        "end_iso": {
                                            "type": "string",
                                            "format": "date-time",
                                            "example": "2024-06-05T23:59:59Z"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Success"}
                    }
                }
            }
        }
    }


@app.post("/tool/summarize_emails")
async def summarize_emails_rest(request: Request):
    """REST endpoint for testing"""
    # Verify API key authentication
    if not verify_api_key(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized: Invalid or missing API key"}
        )
    
    try:
        data = await request.json()
        start_iso = data.get("start_iso")
        end_iso = data.get("end_iso")
        
        if not start_iso or not end_iso:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing start_iso or end_iso"}
            )
        
        result = summarize_emails(start_iso, end_iso)
        return JSONResponse(content=result)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 FastMCP Email Server with MCP SSE Protocol")
    print("=" * 60)
    print("   Port: 5001")
    print("   MCP SSE: http://0.0.0.0:5001/sse")
    print("   OpenAPI: http://0.0.0.0:5001/openapi.json")
    print("   REST Test: http://0.0.0.0:5001/tool/summarize_emails")
    print("=" * 60)
    print("")
    if MCP_API_KEY:
        print("🔒 Authentication: ENABLED")
        print("   Use 'Authorization: Bearer <YOUR_API_KEY>' header")
    else:
        print("⚠️  Authentication: DISABLED (set MCP_API_KEY in .env)")
    print("")
    print("For OpenAI Responses API:")
    print('  server_url: "https://frankimap.ngrok.dev/sse"')
    print('  server_label: "email_summarizer"')
    if MCP_API_KEY:
        print('  auth_method: "Access Token/API key"')
        print('  api_key: <YOUR_MCP_API_KEY>')
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=5001)
