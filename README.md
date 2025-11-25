# Flask Email MCP Server

A Flask-based MCP (Model Context Protocol) server with email reading and summarization capabilities using OpenAI.

## Features

- 📧 **Email Reading**: Connect to IMAP mailbox (Strato) and fetch emails
- ⏰ **Time Range Filtering**: Filter emails by ISO timestamp range
- 🤖 **AI Summarization**: Use OpenAI GPT-4o-mini to summarize emails
- 🔌 **REST API**: Simple Flask REST API for easy integration

## Architecture

```
User/Client → Flask Server → IMAP Server (Strato)
                    ↓
                OpenAI API (GPT-4o-mini)
                    ↓
                Summary Response
```

## Installation

1. **Create virtual environment**:
```bash
cd /Users/frank/projects/ai-agent/flask-email-mcp
python3 -m venv venv
source venv/bin/activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment** (already set in `.env`):
```env
OPENAI_API_KEY=your_openai_key
IMAP_HOST=imap.strato.de
IMAP_USER=frank@family-schulze.de
IMAP_PASS=your_password
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
```

## Usage

### Start the Server

```bash
python app.py
```

Server will start on `http://0.0.0.0:5000`

### API Endpoints

#### Health Check
```bash
curl http://localhost:5000/
```

#### Read and Summarize Emails

**Endpoint**: `POST /tool/read_emails`

**Request Format**:
```json
{
  "intent": "summarize_emails",
  "absolute_time_range": {
    "start_iso": "2024-06-05T00:00:00Z",
    "end_iso": "2024-06-05T23:59:59Z"
  }
}
```

**Example using curl**:
```bash
curl -X POST http://localhost:5000/tool/read_emails \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "summarize_emails",
    "absolute_time_range": {
      "start_iso": "2024-06-05T00:00:00Z",
      "end_iso": "2024-06-05T23:59:59Z"
    }
  }'
```

**Response Format**:
```json
{
  "intent": "summarize_emails",
  "time_range": {
    "start": "2024-06-05T00:00:00Z",
    "end": "2024-06-05T23:59:59Z"
  },
  "email_count": 5,
  "emails": [
    {
      "from": "Sender Name <sender@example.com>",
      "subject": "Email Subject",
      "date": "Wed, 05 Jun 2024 10:30:00 +0200",
      "local_time": "2024-06-05T10:30:00+02:00",
      "utc_timestamp": 1717578600.0,
      "body_preview": "First 200 characters of email body..."
    }
  ],
  "summary": "AI-generated summary of all emails in the time range..."
}
```

### Test Script

Use the included test script to verify the server:

```bash
# Test with example date (June 5, 2024)
python test_request.py

# Test with today's emails
python test_request.py today
```

## How It Works

1. **Client sends request** with intent and ISO time range
2. **Flask server** validates input
3. **IMAP connection** to Strato mailbox
4. **Fetch emails** matching the date range (filtered by actual timestamp)
5. **Extract details**: From, Subject, Date, Body preview
6. **OpenAI API** generates summary of all emails
7. **Response** includes email list and AI summary

## Time Zone Handling

- Input: ISO timestamps in UTC (e.g., `2024-06-05T00:00:00Z`)
- IMAP search: Converted to DD-Mon-YYYY format
- Email dates: Parsed and converted to Europe/Berlin local time
- Output: Both local time (ISO) and UTC timestamp included

## Error Handling

The server handles various error cases:
- Missing IMAP credentials
- IMAP connection failures
- Invalid date formats
- OpenAI API errors
- Email parsing errors

All errors return appropriate HTTP status codes and JSON error messages.

## Dependencies

- **Flask**: Web framework
- **python-dotenv**: Environment variable management
- **openai**: OpenAI API client
- **imapclient**: IMAP email client
- **pyzmail36**: Email parsing
- **email-validator**: Email validation

## Security Notes

- ⚠️ Credentials are stored in `.env` file (not committed to git)
- Use environment variables in production
- Consider using OAuth2 for email authentication
- API should be behind authentication in production

## Future Enhancements

- [ ] Add authentication to Flask endpoints
- [ ] Support multiple mailbox folders (not just INBOX)
- [ ] Add email search by sender/subject
- [ ] Implement caching for repeated queries
- [ ] Add support for multiple IMAP accounts
- [ ] WebSocket support for real-time email notifications
- [ ] Add email composition and sending functionality

## Troubleshooting

### Connection refused
- Make sure Flask server is running: `python app.py`
- Check if port 5000 is available

### IMAP authentication failed
- Verify credentials in `.env` file
- Check if IMAP access is enabled on your Strato account

### No emails returned
- Check date range (use ISO format with 'Z' for UTC)
- Verify emails exist in that time range
- Check server logs for IMAP search details

## License

MIT
