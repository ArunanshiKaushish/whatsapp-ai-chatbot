"""Flask application — WhatsApp webhook and health endpoints."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, request
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from claude_client import ClaudeClient
from config import Config, LOGS_DIR
from database import (
    SessionLocal,
    get_or_create_user,
    get_recent_messages,
    init_db,
    save_message,
)
from memory import extract_and_store_memories, retrieve_relevant_memories

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGS_DIR.mkdir(exist_ok=True)
log_file = LOGS_DIR / "app.log"

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)

file_handler = RotatingFileHandler(
    log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Flask(__name__)
claude_client: ClaudeClient | None = None


def get_claude() -> ClaudeClient:
    global claude_client
    if claude_client is None:
        claude_client = ClaudeClient()
    return claude_client


def validate_twilio_request() -> bool:
    """Validate Twilio webhook signature in production."""
    if Config.FLASK_ENV == "development":
        return True

    validator = RequestValidator(Config.TWILIO_AUTH_TOKEN)
    url = request.url
    # Railway/proxies may use X-Forwarded-* headers
    if request.headers.get("X-Forwarded-Proto"):
        url = request.headers.get("X-Forwarded-Proto", "https") + "://" + request.host + request.path

    signature = request.headers.get("X-Twilio-Signature", "")
    params = request.form.to_dict()
    return validator.validate(url, params, signature)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for deployment platforms."""
    missing = Config.validate()
    status = "ok" if not missing else "degraded"
    return {
        "status": status,
        "service": "whatsapp-ai-chatbot",
        "missing_config": missing,
    }, 200 if status == "ok" else 503


@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Receive incoming WhatsApp messages from Twilio.

    Extracts phone number, message body, and timestamp; generates a Claude
    reply with conversation history and long-term memories; responds via TwiML.
    """
    try:
        if not validate_twilio_request():
            logger.warning("Invalid Twilio signature on incoming request")
            return "Forbidden", 403

        phone_number = request.form.get("From", "").strip()
        message_body = request.form.get("Body", "").strip()
        message_sid = request.form.get("MessageSid", "")
        timestamp = request.form.get("DateSent") or request.form.get("Timestamp", "")

        logger.info(
            "Incoming WhatsApp message | from=%s | sid=%s | time=%s | body=%s",
            phone_number,
            message_sid,
            timestamp,
            message_body[:120],
        )

        if not phone_number:
            logger.error("Missing From field in Twilio webhook")
            return _twiml_reply("Sorry, I could not identify your phone number.")

        if not message_body:
            return _twiml_reply("Please send a text message.")

        missing = Config.validate()
        if missing:
            logger.error("Missing configuration: %s", ", ".join(missing))
            return _twiml_reply(
                "The bot is not fully configured yet. Please try again later."
            )

        session = SessionLocal()
        try:
            user = get_or_create_user(session, phone_number)

            # Load context before saving the new message (history excludes current)
            history = get_recent_messages(
                session, user.id, Config.MAX_HISTORY_MESSAGES
            )
            memories = retrieve_relevant_memories(
                session,
                user.id,
                message_body,
                limit=Config.MAX_MEMORIES_TO_INJECT,
            )
            memory_texts = [m.memory_text for m in memories]

            # Persist user message
            save_message(session, user.id, "user", message_body)

            # Generate Claude reply
            reply = get_claude().generate_reply(
                history=history,
                current_message=message_body,
                memories=memory_texts,
            )

            if not reply:
                reply = "I'm sorry, I couldn't generate a response. Please try again."

            # Persist assistant reply
            save_message(session, user.id, "assistant", reply)

            # Extract and store long-term memories asynchronously-safe (inline)
            extract_and_store_memories(
                session,
                user.id,
                message_body,
                reply,
                claude_extract_fn=get_claude().extract_memories,
            )

            session.commit()
            logger.info("Replied to %s | reply_len=%d", phone_number, len(reply))
            return _twiml_reply(reply)

        except Exception:
            session.rollback()
            logger.exception("Error processing message from %s", phone_number)
            return _twiml_reply(
                "Something went wrong while processing your message. Please try again."
            )
        finally:
            session.close()

    except Exception:
        logger.exception("Unhandled error in webhook")
        return _twiml_reply("An unexpected error occurred. Please try again later.")


def _twiml_reply(message: str) -> str:
    """Build a TwiML MessagingResponse."""
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)


@app.before_request
def log_request():
    if request.path.startswith("/webhook"):
        logger.debug("%s %s", request.method, request.path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

init_db()

if __name__ == "__main__":
    missing = Config.validate()
    if missing:
        logger.warning(
            "Starting with missing config (some features will fail): %s",
            ", ".join(missing),
        )
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.FLASK_ENV == "development")
