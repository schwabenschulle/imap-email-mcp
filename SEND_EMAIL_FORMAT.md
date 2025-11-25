# Send Email Tool - JSON Format

## Tool Name: `send_email`

### Description
Send an email to one or more recipients with support for CC, BCC, and HTML content.

## JSON Request Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "send_email",
    "arguments": {
      "to": ["recipient@example.com"],
      "subject": "Your Subject Here",
      "body": "Your email body content here",
      "cc": ["optional-cc@example.com"],
      "bcc": ["optional-bcc@example.com"],
      "body_type": "plain"
    }
  }
}
```

## Parameters

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `to` | array | ✅ Yes | List of recipient email addresses | `["user@example.com", "another@example.com"]` |
| `subject` | string | ✅ Yes | Email subject line | `"Meeting Summary"` |
| `body` | string | ✅ Yes | Email body content (plain text or HTML) | `"Hello, this is the email body..."` |
| `cc` | array | ❌ No | Optional list of CC recipients | `["cc@example.com"]` |
| `bcc` | array | ❌ No | Optional list of BCC recipients | `["bcc@example.com"]` |
| `body_type` | string | ❌ No | Email body type: `"plain"` or `"html"` (default: `"plain"`) | `"html"` |

## Examples

### Example 1: Simple Email
```json
{
  "to": ["john@example.com"],
  "subject": "Quick Update",
  "body": "Hi John,\n\nJust wanted to give you a quick update on the project.\n\nBest regards,\nFrank"
}
```

### Example 2: Email with CC and BCC
```json
{
  "to": ["team@example.com"],
  "cc": ["manager@example.com"],
  "bcc": ["hr@example.com"],
  "subject": "Team Meeting Notes",
  "body": "Here are the notes from today's team meeting...\n\n1. Project updates\n2. Next steps\n3. Action items"
}
```

### Example 3: HTML Email
```json
{
  "to": ["customer@example.com"],
  "subject": "Welcome to Our Service!",
  "body": "<html><body><h1>Welcome!</h1><p>Thank you for signing up. We're excited to have you!</p><p><strong>Get started now:</strong> <a href='https://example.com'>Click here</a></p></body></html>",
  "body_type": "html"
}
```

### Example 4: Multiple Recipients
```json
{
  "to": ["alice@example.com", "bob@example.com", "carol@example.com"],
  "subject": "Team Outing Next Week",
  "body": "Hi everyone,\n\nLooking forward to our team outing next Friday!\n\nCheers,\nFrank"
}
```

## Response Format

### Success Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{
  \"status\": \"success\",
  \"message\": \"Email sent successfully\",
  \"recipients\": {
    \"to\": [\"recipient@example.com\"],
    \"cc\": [],
    \"bcc\": []
  },
  \"subject\": \"Your Subject Here\",
  \"sent_at\": \"2025-11-24T15:30:45+01:00\"
}"
      }
    ]
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error": "SMTP authentication failed",
  "message": "Failed to send email: SMTP authentication failed"
}
```

## Testing

### Via curl (MCP Protocol)
```bash
curl -X POST https://frankimap.ngrok.dev/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "send_email",
      "arguments": {
        "to": ["your-email@example.com"],
        "subject": "Test from MCP Server",
        "body": "This is a test email!"
      }
    }
  }'
```

### Via OpenAI Agent
Simply ask the agent:
- "Send an email to john@example.com with subject 'Meeting Tomorrow' saying we should meet at 3pm"
- "Email the team at team@company.com about the project update"
- "Write an email to customer@example.com thanking them for their purchase"

The agent will automatically format the request correctly and call the tool.

## Configuration

Add these settings to your `.env` file:
```env
# SMTP Configuration
SMTP_HOST=smtp.strato.de
SMTP_PORT=465
EMAIL_FROM_NAME=Frank Schulze

# Existing IMAP settings
IMAP_USER=frank@family-schulze.de
IMAP_PASS=your_password
```

## Notes

- **From Address**: Emails are sent from the `IMAP_USER` address configured in `.env`
- **From Name**: The display name is set via `EMAIL_FROM_NAME` in `.env`
- **Security**: Uses SMTP over SSL (port 465) for secure transmission
- **Authentication**: Uses the same credentials as IMAP (IMAP_USER and IMAP_PASS)
- **Body Types**: 
  - `"plain"` - Plain text email (default)
  - `"html"` - HTML formatted email

## Common Use Cases

1. **Sending status updates** to team members
2. **Automated notifications** based on email summaries
3. **Forwarding information** from incoming emails
4. **Sending reminders** or follow-ups
5. **Replying to emails** programmatically
