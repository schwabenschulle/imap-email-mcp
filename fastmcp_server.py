#!/usr/bin/env python3
"""
FastMCP Email Server with OpenAPI Support
A proper MCP server using FastMCP framework for email reading and summarization.
Includes OpenAPI endpoint for OpenAI Agent Builder.
"""
import os
import sys
from datetime import datetime
from typing import Dict, Any
import imaplib
import ssl
import email
from email.header import decode_header
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import FastMCP
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

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

# Initialize FastMCP server
mcp = FastMCP("Email Summarizer 📧", version="1.0.0")


def fetch_emails_from_imap(start_iso: str, end_iso: str) -> list:
    """
    Fetch emails from IMAP server within the specified time range.
    
    Args:
        start_iso: Start time in ISO format (UTC)
        end_iso: End time in ISO format (UTC)
    
    Returns:
        List of email dictionaries
    """
    try:
        # Parse ISO timestamps
        start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
        
        # Connect to IMAP
        ssl_context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=ssl_context)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("INBOX")
        
        # Search emails by date
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
            
            # Parse email
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Extract date
            date_str = msg.get("Date", "")
            try:
                email_date = email.utils.parsedate_to_datetime(date_str)
                if email_date.tzinfo is None:
                    email_date = email_date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
                
                # Filter by timestamp
                if not (start_dt <= email_date <= end_dt):
                    continue
                
                # Extract subject
                subject = ""
                if msg.get("Subject"):
                    decoded = decode_header(msg["Subject"])[0]
                    if isinstance(decoded[0], bytes):
                        subject = decoded[0].decode(decoded[1] or "utf-8", errors="ignore")
                    else:
                        subject = decoded[0]
                
                # Extract from
                from_header = msg.get("From", "")
                
                # Extract body preview
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
    """
    Generate AI summary of emails using OpenAI.
    
    Args:
        emails: List of email dictionaries
    
    Returns:
        Summary text
    """
    if not emails:
        return "No emails found in the specified time range."
    
    try:
        # Prepare email content for summarization
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


@mcp.tool()
def summarize_emails(start_iso: str, end_iso: str) -> Dict[str, Any]:
    """
    Fetch and summarize emails from a specified time range.
    
    Use this tool when the user asks about emails from a specific date or time period.
    Always provide ISO 8601 timestamps in UTC with Z suffix.
    
    Args:
        start_iso: Start time in ISO 8601 format with Z suffix (e.g., "2024-06-05T00:00:00Z")
        end_iso: End time in ISO 8601 format with Z suffix (e.g., "2024-06-05T23:59:59Z")
    
    Returns:
        Dictionary containing email count, list of emails, and AI-generated summary
    
    Examples:
        >>> summarize_emails("2024-06-05T00:00:00Z", "2024-06-05T23:59:59Z")
        >>> summarize_emails("2025-11-24T00:00:00Z", "2025-11-24T23:59:59Z")
    """
    try:
        # Fetch emails
        emails = fetch_emails_from_imap(start_iso, end_iso)
        
        # Generate summary
        summary = generate_summary(emails)
        
        return {
            "time_range": {
                "start": start_iso,
                "end": end_iso
            },
            "email_count": len(emails),
            "emails": emails,
            "summary": summary
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "time_range": {
                "start": start_iso,
                "end": end_iso
            },
            "email_count": 0,
            "emails": [],
            "summary": f"Error: {e}"
        }


# Create FastAPI app for OpenAPI endpoint
app = FastAPI(title="Email Summarizer API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://platform.openai.com", "https://chat.openai.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "FastMCP Email Server",
        "status": "running",
        "version": "1.0.0",
        "mcp_endpoint": "/mcp",
        "openapi_schema": "/openapi.json"
    }

@app.get("/openapi.json")
async def get_openapi_schema(request: Request):
    """OpenAPI schema for OpenAI Agent Builder"""
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Email Summarizer API",
            "description": "Read and summarize emails from IMAP mailbox in specified time range",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": base_url,
                "description": "FastMCP Email Server"
            }
        ],
        "paths": {
            "/tool/summarize_emails": {
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
                    },
                    "responses": {
                        "200": {
                            "description": "Email summary response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
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

@app.post("/tool/summarize_emails")
async def summarize_emails_endpoint(request: Request):
    """REST endpoint for email summarization"""
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


@app.get("/sse")
async def sse_endpoint():
    """SSE endpoint for MCP protocol (OpenAI Responses API)"""
    return {
        "message": "MCP SSE endpoint",
        "note": "This endpoint requires proper MCP SSE client connection",
        "server_label": "email_summarizer",
        "tools_available": ["summarize_emails"]
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting FastMCP Email Server")
    print("=" * 60)
    print("   Port: 5001")
    print("   SSE Endpoint (for OpenAI): http://0.0.0.0:5001/sse")
    print("   OpenAPI Schema: http://0.0.0.0:5001/openapi.json")
    print("   REST Tool: http://0.0.0.0:5001/tool/summarize_emails")
    print("=" * 60)
    print("")
    print("For OpenAI Responses API, use:")
    print('  server_url: "https://frankimap.ngrok.dev/sse"')
    print("")
    
    # Run FastAPI server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
