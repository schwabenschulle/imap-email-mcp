#!/usr/bin/env python3
"""
FastMCP Email Server with proper SSE support for OpenAI Responses API
"""
import os
import sys
import json
import re
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
from bs4 import BeautifulSoup

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


def fetch_emails_from_imap(start_iso: str, end_iso: str, sender_filter: Optional[str] = None, max_emails: int = 50) -> list:
    """Fetch emails from IMAP server within the specified time range.
    
    Args:
        start_iso: Start time in ISO format
        end_iso: End time in ISO format
        sender_filter: Optional email address or domain to filter by (e.g., 'service.paypal.com')
        max_emails: Maximum number of emails to fetch (default: 50)
    """
    mail = None
    try:
        start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
        
        print(f"[INFO] Connecting to IMAP server: {IMAP_HOST}:993", flush=True)
        ssl_context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=ssl_context)
        
        # Login
        print(f"[INFO] Logging in as: {IMAP_USER}", flush=True)
        status, response = mail.login(IMAP_USER, IMAP_PASS)
        if status != "OK":
            raise Exception(f"IMAP login failed: {response}")
        print(f"[INFO] IMAP login successful", flush=True)
        
        # Select mailbox
        print(f"[INFO] Selecting INBOX...", flush=True)
        status, response = mail.select("INBOX")
        if status != "OK":
            raise Exception(f"IMAP select INBOX failed: {response}")
        print(f"[INFO] INBOX selected, {response[0].decode()} messages", flush=True)
        
        search_date = start_dt.strftime("%d-%b-%Y")
        
        # Build search criteria
        if sender_filter:
            search_criteria = f'(SINCE "{search_date}" FROM "{sender_filter}")'
        else:
            search_criteria = f'(SINCE "{search_date}")'
        
        print(f"[INFO] Searching with criteria: {search_criteria}", flush=True)
        status, messages = mail.search(None, search_criteria)
        
        if status != "OK":
            print(f"[ERROR] IMAP search failed: status={status}, messages={messages}", file=sys.stderr, flush=True)
            return []
        
        print(f"[INFO] Search successful, found {len(messages[0].split())} messages", flush=True)
        
        email_ids = messages[0].split()
        emails = []
        
        # Limit the number of emails to process
        email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
        
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
                
                # Extract FULL email body - PayPal details can be deep in the email
                body_plain = ""
                body_html_raw = ""
                body_html_parsed = ""
                
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        
                        # Get plain text version (FULL, not truncated)
                        if content_type == "text/plain" and not body_plain:
                            try:
                                body_plain = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            except:
                                pass
                        
                        # Get HTML version (FULL, not truncated)
                        elif content_type == "text/html" and not body_html_raw:
                            try:
                                body_html_raw = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            except:
                                pass
                else:
                    try:
                        payload = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                        if msg.get_content_type() == "text/plain":
                            body_plain = payload
                        else:
                            body_html_raw = payload
                    except:
                        pass
                
                # Parse HTML to readable text if we have HTML
                if body_html_raw:
                    try:
                        soup = BeautifulSoup(body_html_raw, 'lxml')
                        
                        # Remove script, style, and meta elements
                        for element in soup(["script", "style", "meta", "link"]):
                            element.decompose()
                        
                        # Get text and clean it up
                        text = soup.get_text(separator=' ', strip=True)
                        
                        # Clean up whitespace
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        body_html_parsed = ' '.join(chunk for chunk in chunks if chunk)
                        
                        print(f"[INFO] Parsed HTML: {len(body_html_parsed)} chars from {len(body_html_raw)} HTML chars", flush=True)
                    except Exception as e:
                        print(f"[WARNING] BeautifulSoup parsing failed: {e}", flush=True)
                        # Fallback to simple regex
                        body_html_parsed = re.sub(r'<[^>]+>', ' ', body_html_raw)
                        body_html_parsed = re.sub(r'\s+', ' ', body_html_parsed).strip()
                
                # Use the best available content, but limit to 10000 chars for API
                body_preview = body_plain or body_html_parsed or ""
                body_preview = body_preview[:10000]  # Increased from 3000 to 10000!
                
                if not body_preview:
                    print(f"[WARNING] No body content extracted for email: {subject}", flush=True)
                
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
        
        print(f"[INFO] Closing IMAP connection", flush=True)
        mail.close()
        mail.logout()
        return emails
    
    except Exception as e:
        print(f"[ERROR] IMAP error: {e}", file=sys.stderr, flush=True)
        # Attempt to cleanup connection
        if mail:
            try:
                mail.logout()
            except:
                pass
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
            model="gpt-5.1",  # Using GPT-5.1 as requested
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert data extraction specialist for emails, particularly payment notifications.

CRITICAL: You must extract EXACT information from the email body text provided. Do NOT say "N/A" unless the information is truly missing.

For PayPal payment emails (subject: "Du hast eine Zahlung erhalten"):
1. Look for the AMOUNT - patterns:
   - "Zahlung in Höhe von 45,00 EUR"
   - "Sie haben 120,50 € erhalten"
   - Numbers with EUR or € symbol

2. Look for PAYER NAME - patterns:
   - "von [Name]"
   - "from [Name]"
   - After "Absender:" or "Sender:"
   - Near the amount information

3. Look for TRANSACTION ID - patterns:
   - "Transaktionscode:"
   - "Transaction ID:"
   - Long alphanumeric codes (e.g., 1AB234567CD890123)

4. Look for COMMENT/PURPOSE - patterns:
   - "Nachricht:" or "Message:"
   - "Verwendungszweck:"
   - Any text after "Der Käufer hat folgende Nachricht hinterlassen:"

5. Extract DATE/TIME from the email

Create a detailed table with ALL extracted information for EACH email. If you find the information in the body text, include it!"""
                },
                {
                    "role": "user",
                    "content": f"Extract detailed payment information from these {len(emails)} emails. Each email body contains up to 2000 characters with all details:\n\n{email_text}"
                }
            ],
            temperature=0.1,  # Lower for more precise extraction
            max_tokens=4000  # More tokens for detailed output
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"[ERROR] OpenAI error: {e}", file=sys.stderr)
        return f"Error generating summary: {e}"


def summarize_emails(start_iso: str, end_iso: str, sender_filter: Optional[str] = None, max_emails: int = 50) -> Dict[str, Any]:
    """Main tool function for email summarization.
    
    Args:
        start_iso: Start time in ISO format
        end_iso: End time in ISO format
        sender_filter: Optional email address or domain to filter by
        max_emails: Maximum number of emails to summarize (default: 50)
    """
    try:
        emails = fetch_emails_from_imap(start_iso, end_iso, sender_filter, max_emails)
        summary = generate_summary(emails)
        
        return {
            "time_range": {"start": start_iso, "end": end_iso},
            "email_count": len(emails),
            "emails": emails,
            "summary": summary,
            "note": f"Limited to {max_emails} most recent emails" if sender_filter else f"Limited to {max_emails} emails"
        }
    except Exception as e:
        return {
            "error": str(e),
            "time_range": {"start": start_iso, "end": end_iso},
            "email_count": 0,
            "emails": [],
            "summary": f"Error: {e}"
        }


def read_emails(start_iso: str, end_iso: str, sender_filter: Optional[str] = None, max_emails: int = 50) -> Dict[str, Any]:
    """Read and return full email content without AI summarization.
    
    Args:
        start_iso: Start time in ISO format
        end_iso: End time in ISO format  
        sender_filter: Optional email address or domain to filter by
        max_emails: Maximum number of emails to return (default: 50)
    """
    try:
        emails = fetch_emails_from_imap(start_iso, end_iso, sender_filter, max_emails)
        
        return {
            "time_range": {"start": start_iso, "end": end_iso},
            "email_count": len(emails),
            "emails": emails,
            "note": f"Limited to {max_emails} most recent emails" if sender_filter else f"Limited to {max_emails} emails"
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
                            "description": "Fetch and summarize emails from a specified time range. Use this when the user asks about emails from a specific date or time period. Always provide ISO 8601 timestamps in UTC with Z suffix. Supports filtering by sender to reduce token usage.",
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
                                    },
                                    "sender_filter": {
                                        "type": "string",
                                        "description": "Optional: Filter emails by sender email address or domain (e.g., 'service.paypal.com', 'noreply@example.com')"
                                    },
                                    "max_emails": {
                                        "type": "integer",
                                        "description": "Maximum number of emails to process (default: 50, prevents token overflow)",
                                        "default": 50
                                    }
                                },
                                "required": ["start_iso", "end_iso"]
                            }
                        },
                        {
                            "name": "read_emails",
                            "description": "Fetch and return full email content from a specified time range without AI summarization. Use this when the user wants to see the complete emails. Always provide ISO 8601 timestamps in UTC with Z suffix. Supports filtering by sender to reduce token usage.",
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
                                    },
                                    "sender_filter": {
                                        "type": "string",
                                        "description": "Optional: Filter emails by sender email address or domain (e.g., 'service.paypal.com', 'noreply@example.com')"
                                    },
                                    "max_emails": {
                                        "type": "integer",
                                        "description": "Maximum number of emails to return (default: 50, prevents token overflow)",
                                        "default": 50
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
                sender_filter = arguments.get("sender_filter")
                max_emails = arguments.get("max_emails", 50)
                
                result = summarize_emails(start_iso, end_iso, sender_filter, max_emails)
                
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
                sender_filter = arguments.get("sender_filter")
                max_emails = arguments.get("max_emails", 50)
                
                result = read_emails(start_iso, end_iso, sender_filter, max_emails)
                
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
                # Convert to list if it's a string
                if isinstance(to, str):
                    to = [to]
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
