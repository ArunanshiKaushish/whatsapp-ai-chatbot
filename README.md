# WhatsApp AI Chatbot

A production-ready WhatsApp chatbot powered by **Twilio**, **Anthropic Claude**, and **SQLite** with persistent per-user conversation history and long-term memory.

## Features

- Receives WhatsApp messages via Twilio webhooks
- Replies using the Anthropic Claude API
- Per-user conversation history (last 20 messages)
- Long-term memory extraction and keyword-based retrieval
- Multi-user support with isolated data per phone number
- Structured logging to `logs/app.log`
- Railway deployment ready

## Project Structure

```
whatsapp-ai-chatbot/
├── app.py                 # Flask app & WhatsApp webhook
├── claude_client.py       # Anthropic Claude integration
├── config.py              # Environment configuration
├── database.py            # SQLAlchemy session & helpers
├── memory.py              # Long-term memory system
├── models.py              # ORM models (users, messages, memories)
├── verify_setup.py        # Local verification script
├── requirements.txt
├── Procfile               # Railway/Heroku process file
├── railway.json           # Railway deployment config
├── runtime.txt            # Python version
├── .env.example           # Environment variable template
├── prompts/
│   └── system_prompt.txt  # Configurable assistant personality
├── data/                  # SQLite database (created at runtime)
└── logs/                  # Application logs
```

## Prerequisites

- Python 3.12+
- [Twilio account](https://www.twilio.com/try-twilio) with WhatsApp Sandbox or approved number
- [Anthropic API key](https://console.anthropic.com/)

## Installation

```bash
git clone <your-repo-url>
cd whatsapp-ai-chatbot

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | Your Twilio WhatsApp number (e.g. `whatsapp:+14155238886`) |
| `CLAUDE_MODEL` | Claude model ID (default: `claude-sonnet-4-20250514`) |
| `FLASK_ENV` | `development` or `production` |

**Never commit `.env` to version control.**

## Running Locally

```bash
# Set FLASK_ENV=development in .env to skip Twilio signature validation
python app.py
```

The server starts on `http://localhost:5000`.

### Local Webhook Testing with ngrok

Twilio needs a public HTTPS URL. Use [ngrok](https://ngrok.com/):

```bash
ngrok http 5000
```

Copy the HTTPS URL (e.g. `https://abc123.ngrok.io`) and configure Twilio:

**Webhook URL:** `https://abc123.ngrok.io/webhook/whatsapp`  
**HTTP Method:** `POST`

## Twilio Setup

1. Go to [Twilio Console](https://console.twilio.com/) → **Messaging** → **Try it out** → **Send a WhatsApp message** (Sandbox) or configure your WhatsApp Sender.
2. Under **Sandbox Settings** (or your WhatsApp Sender configuration), set:
   - **When a message comes in:** `https://YOUR_DOMAIN/webhook/whatsapp`
   - **Method:** `POST`
3. Join the sandbox by sending the join code to the sandbox number from your phone.
4. Send a message — the bot should reply within a few seconds.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook/whatsapp` | POST | Twilio incoming message webhook |
| `/health` | GET | Health check for deployment |

## How Memory Works

1. **Conversation history** — Last 20 user/assistant messages are loaded per request.
2. **Long-term memories** — After each exchange, Claude extracts durable facts (name, preferences, etc.) and stores them in the `memories` table.
3. **Retrieval** — Before each reply, relevant memories are found via semantic keyword matching against the current message.
4. **Context order** sent to Claude:
   - System prompt
   - Relevant memories
   - Recent chat history
   - Current message

### Example

```
User (Week 1): "My name is Arunanshi."
→ Stored: "User's name is Arunanshi."

User (Week 3): "What is my name?"
→ Memory retrieved → Claude replies: "Your name is Arunanshi."
```

## Deploying to Railway

1. Push this repository to GitHub.
2. Create a new project on [Railway](https://railway.app/).
3. Connect your GitHub repository.
4. Add environment variables from `.env.example` in the Railway dashboard.
5. Railway auto-detects the `Procfile` and deploys.
6. Copy your Railway public URL (e.g. `https://your-app.up.railway.app`).
7. Set the Twilio webhook to: `https://your-app.up.railway.app/webhook/whatsapp`

### Railway Environment Variables

Set all variables from `.env.example`. Railway provides `PORT` automatically.

> **Note:** SQLite data on Railway is ephemeral unless you attach a persistent volume. For production, consider mounting a volume at `/app/data` or switching `DATABASE_URL` to PostgreSQL.

## Verification

Run the built-in verification script:

```bash
python verify_setup.py
```

This tests database persistence, multi-user isolation, memory retrieval, and Flask endpoints without requiring live API keys.

## Logging

Logs are written to `logs/app.log` with rotation (5 MB × 5 files). Events logged:

- Incoming WhatsApp messages
- Claude API requests and responses
- Memory saves and updates
- Errors and exceptions

## Customizing Personality

Edit `prompts/system_prompt.txt` to change the assistant's behavior. Changes take effect on the next request (no restart needed if using a process manager with auto-reload).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot doesn't reply | Check Railway logs; verify all env vars are set |
| 403 Forbidden from webhook | Ensure `TWILIO_AUTH_TOKEN` is correct; in dev set `FLASK_ENV=development` |
| Claude errors | Verify `ANTHROPIC_API_KEY` and `CLAUDE_MODEL` |
| Memory not working | Check `logs/app.log` for extraction errors |
| ngrok URL changed | Update Twilio webhook URL each time ngrok restarts (free tier) |

## License

MIT
