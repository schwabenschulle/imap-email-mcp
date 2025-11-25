# OpenAI Integration Guide

## New Endpoints Available

Your Flask server now provides OpenAPI schema endpoints:

1. **OpenAPI Schema**: `https://YOUR-URL.ngrok-free.dev/openapi.json`
2. **AI Plugin Manifest**: `https://YOUR-URL.ngrok-free.dev/.well-known/ai-plugin.json`
3. **Health Check**: `https://YOUR-URL.ngrok-free.dev/`

## How to Connect to OpenAI

### Option 1: Custom GPT (ChatGPT Plus)

1. Go to https://chat.openai.com
2. Click your profile → "My GPTs" → "Create a GPT"
3. Go to "Configure" tab
4. Scroll to "Actions" section
5. Click "Create new action"
6. **Import from URL**: Paste your OpenAPI URL:
   ```
   https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json
   ```
7. Click "Test" to verify
8. Save your GPT

### Option 2: OpenAI Playground (API)

1. Go to https://platform.openai.com/playground
2. Add a custom action/function
3. Import from URL or paste the schema

### Option 3: Manual Schema Import

If the URL import doesn't work, copy the schema:

```bash
curl https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json
```

Then paste the JSON into OpenAI's action editor.

## Testing Your Integration

Once connected, you can ask ChatGPT:

- **"Check my emails from June 5th, 2024"**
- **"Summarize emails from 2024-06-05"**
- **"What emails did I receive between June 5 00:00 and June 5 23:59 in 2024?"**

ChatGPT will automatically:
1. Convert your natural language to the required JSON format
2. Call your API with proper ISO timestamps
3. Present the summary in a friendly way

## Expected OpenAI Request

When ChatGPT calls your API, it will send:

```json
{
  "intent": "summarize_emails",
  "absolute_time_range": {
    "start_iso": "2024-06-05T00:00:00Z",
    "end_iso": "2024-06-05T23:59:59Z"
  }
}
```

## Monitoring

- **ngrok web interface**: http://127.0.0.1:4040
- **Flask logs**: Check your terminal running `python app.py`

## Troubleshooting

### "Could not load action"
- Make sure Flask is running
- Make sure ngrok is running
- Check the URL is correct (ends in `.dev` not `.app` or `.io`)

### "Action failed to execute"
- Check Flask logs for errors
- Verify IMAP credentials in `.env`
- Test with curl first to make sure it works

### "Invalid schema"
- Visit the OpenAPI URL directly in browser to see if it loads
- Check for JSON syntax errors

## Your Current Setup

**Flask Server**: Port 5001 (localhost)
**ngrok URL**: https://hellen-sarraceniaceous-adelina.ngrok-free.dev
**OpenAPI Schema**: https://hellen-sarraceniaceous-adelina.ngrok-free.dev/openapi.json

## Important Notes

⚠️ **Free ngrok URL changes on restart** - You'll need to update OpenAI configuration if you restart ngrok

⚠️ **No authentication** - Anyone with the URL can use your API (add auth for production)

⚠️ **API calls IMAP directly** - Make sure your mail server allows the connections

✅ **Auto-generates schema** - The `request.url_root` dynamically includes your ngrok URL
