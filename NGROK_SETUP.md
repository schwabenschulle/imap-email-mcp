# How to Expose Flask Server with ngrok

## Quick Start

### Terminal 1: Start Flask Server
```bash
cd /Users/frank/projects/ai-agent/flask-email-mcp
source venv/bin/activate
python app.py
```

### Terminal 2: Start ngrok
```bash
./start_ngrok.sh
```

Or manually:
```bash
ngrok http 5001
```

## You'll See Output Like:

```
Session Status                online
Account                       YOUR_EMAIL (Plan: Free)
Version                       3.x.x
Region                        Europe (eu)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:5001
```

## 📋 Copy Your Public URL

Your public endpoint will be:
```
https://abc123.ngrok.io/tool/read_emails
```

## 🧪 Test from Anywhere

```bash
curl -X POST https://YOUR-URL.ngrok.io/tool/read_emails \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "summarize_emails",
    "absolute_time_range": {
      "start_iso": "2024-06-05T00:00:00Z",
      "end_iso": "2024-06-05T23:59:59Z"
    }
  }'
```

## 🤖 Configure in OpenAI Custom GPT/Actions

1. Go to https://platform.openai.com/ or ChatGPT settings
2. Create/Edit Custom GPT → Actions
3. Paste this OpenAPI schema (update the URL):

```yaml
openapi: 3.0.0
info:
  title: Email Summarization API
  description: Read and summarize emails from IMAP mailbox in specified time range
  version: 1.0.0
servers:
  - url: https://YOUR-NGROK-URL.ngrok.io
    description: Flask Email MCP Server via ngrok
paths:
  /tool/read_emails:
    post:
      operationId: summarize_emails
      summary: Read and summarize emails in time range
      description: Fetches emails from IMAP mailbox within specified ISO timestamp range and generates AI summary
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - intent
                - absolute_time_range
              properties:
                intent:
                  type: string
                  enum: [summarize_emails]
                  description: Action to perform
                absolute_time_range:
                  type: object
                  required:
                    - start_iso
                    - end_iso
                  properties:
                    start_iso:
                      type: string
                      format: date-time
                      description: Start time in ISO format (e.g., 2024-06-05T00:00:00Z)
                      example: "2024-06-05T00:00:00Z"
                    end_iso:
                      type: string
                      format: date-time
                      description: End time in ISO format (e.g., 2024-06-05T23:59:59Z)
                      example: "2024-06-05T23:59:59Z"
      responses:
        '200':
          description: Email summary response
          content:
            application/json:
              schema:
                type: object
                properties:
                  intent:
                    type: string
                  time_range:
                    type: object
                  email_count:
                    type: integer
                  emails:
                    type: array
                  summary:
                    type: string
        '400':
          description: Bad request
        '500':
          description: Server error
```

## 📊 Monitor Requests

ngrok provides a web interface to see all requests:
```
http://127.0.0.1:4040
```

Open this in your browser to see:
- All incoming requests
- Request/response bodies
- Timing information
- Replay requests

## ⚠️ Important Notes

### Free Plan Limitations
- URL changes every time you restart ngrok
- 40 connections per minute limit
- Session expires after 2 hours (reconnect needed)

### Security Considerations
- Anyone with the URL can access your endpoint
- Your IMAP credentials are in .env (not exposed, but API can read emails)
- Consider adding authentication for production use

### Upgrade ngrok (Optional)
For a permanent URL and better limits:
```bash
# Sign up at https://ngrok.com
ngrok config add-authtoken YOUR_AUTH_TOKEN

# Use custom subdomain (paid plan)
ngrok http 5001 --subdomain=frank-email-api
```

## 🔧 Troubleshooting

### ngrok says "connection refused"
Make sure Flask is running on port 5001:
```bash
lsof -i :5001
```

### Can't connect from OpenAI
- Check ngrok is still running (free plan expires)
- Verify the URL is correct (https, not http)
- Check Flask logs for errors

### Slow responses
- OpenAI API calls take 3-10 seconds
- IMAP fetching adds 1-5 seconds
- ngrok adds minimal latency

## 🎯 Example OpenAI Prompts

Once configured, you can ask:
- "Check my emails from June 5th, 2024"
- "Summarize emails from last week"
- "What emails did I get on 2024-06-05?"

OpenAI will automatically call your API with the correct ISO format!
