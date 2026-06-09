# WhatsApp AI Chatbot — Project Handover Document

This document explains what was built, where everything lives, and how to run it.  
Intended for the project owner receiving full rights to this codebase.

---

## What This Project Does

A **WhatsApp chatbot** that:

1. Receives messages from users via **Twilio WhatsApp API**
2. Sends messages to **Anthropic Claude AI** for intelligent replies
3. Remembers each user's conversation history (last 20 messages)
4. Stores **long-term memories** (names, preferences, facts) in SQLite
5. Supports **multiple users** at the same time, each with separate memory
6. Runs on **Railway** (cloud) with a public webhook URL

---

## Project Location

| Item | Path / URL |
|------|------------|
| Local folder | `C:\Users\arunk\Projects\whatsapp-ai-chatbot` |
| GitHub repo | https://github.com/ArunanshiKaushish/whatsapp-ai-chatbot |
| Live app (Railway) | https://web-production-562f2.up.railway.app |
| Health check | https://web-production-562f2.up.railway.app/health |
| WhatsApp webhook | https://web-production-562f2.up.railway.app/webhook/whatsapp |

---

## File Structure (What Each File Does)

```
whatsapp-ai-chatbot/
├── app.py              → Main Flask app; Twilio webhook endpoint
├── claude_client.py    → Sends/receives messages from Claude API
├── gemini_client.py    → Optional backup AI provider (Google Gemini)
├── llm_client.py       → Picks Claude or Gemini based on config
├── config.py           → Reads settings from .env
├── database.py         → SQLite database helpers
├── models.py           → Database tables: users, messages, memories
├── memory.py           → Long-term memory save/retrieve/update
├── test_api_key.py     → Test if Claude API key works
├── verify_setup.py     → Test database and app without WhatsApp
├── prompts/
│   └── system_prompt.txt → Bot personality / instructions
├── data/               → SQLite database (created at runtime)
├── logs/app.log        → Application logs
├── .env                → Secret keys (NEVER commit to GitHub)
├── .env.example        → Template for required variables
├── Procfile            → Tells Railway how to start the app
├── railway.json        → Railway deployment settings
└── README.md           → Full technical documentation
```

---

## Technologies Used

| Technology | Purpose |
|------------|---------|
| Python 3.12+ | Programming language |
| Flask | Web server for webhook |
| Anthropic Claude API | AI brain |
| Twilio | WhatsApp messaging |
| SQLite + SQLAlchemy | Database for history & memory |
| Railway | Cloud hosting |
| Gunicorn | Production web server |

---

## How a Message Flows

```
User sends WhatsApp message
        ↓
Twilio receives it
        ↓
Twilio POSTs to /webhook/whatsapp on Railway
        ↓
app.py extracts phone number + message text
        ↓
database.py loads user + last 20 messages
memory.py loads relevant long-term memories
        ↓
claude_client.py sends context to Claude API
        ↓
Claude generates reply
        ↓
Reply saved to database + memories extracted
        ↓
TwiML response sent back → user sees reply on WhatsApp
```

---

## Required Accounts & Keys

| Service | What you need | Where to get it |
|---------|---------------|-----------------|
| Anthropic | API key + free credits | https://console.anthropic.com |
| Twilio | Account SID, Auth Token, WhatsApp number | https://console.twilio.com |
| Railway | Deployed app + env variables | https://railway.app |
| GitHub | Code repository | https://github.com |

---

## Environment Variables

Set these in `.env` (local) and Railway (production):

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
CLAUDE_MODEL=claude-sonnet-4-6
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
FLASK_ENV=production
```

---

## Work Completed

1. Built full WhatsApp + Claude chatbot with persistent memory
2. Created SQLite database schema (users, messages, memories)
3. Implemented long-term memory extraction and keyword retrieval
4. Deployed to Railway with health check and logging
5. Connected Twilio WhatsApp sandbox webhook
6. Added API key diagnostic tool (`test_api_key.py`)
7. Added optional Gemini provider as fallback
8. Pushed codebase to GitHub

---

## Known Issue (Being Resolved)

**Anthropic API 401 error** — The API key returns "invalid authentication credentials."

This means the key value is wrong or the Anthropic account has not claimed free starter credits yet.  
**Not a code bug** — the app reaches Claude correctly but Claude rejects the key.

**Fix:** Claim free credits at console.anthropic.com → create new API key → update `.env` and Railway.

---

## Copyright / Ownership

Upon successful delivery, full rights to this codebase, deployment, and documentation transfer to the project owner.  
Repository: https://github.com/ArunanshiKaushish/whatsapp-ai-chatbot

---

## Support Commands

```powershell
# Test Claude API key
python test_api_key.py

# Test database + app locally
python verify_setup.py

# Run locally
python app.py

# Push code to GitHub
git add .
git commit -m "your message"
git push
```
