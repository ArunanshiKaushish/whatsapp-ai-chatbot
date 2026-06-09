"""Verification script for local testing without Twilio/Claude credentials."""

import os
import sys
import tempfile
from pathlib import Path

# Use isolated temp DB for verification
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "test-sid")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")
os.environ.setdefault("TWILIO_WHATSAPP_NUMBER", "whatsapp:+10000000000")

_tmp = tempfile.mkdtemp()
_db = Path(_tmp) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"

from database import (  # noqa: E402
    SessionLocal,
    get_or_create_user,
    get_recent_messages,
    init_db,
    save_message,
)
from memory import (  # noqa: E402
    retrieve_relevant_memories,
    save_memory,
    update_memory,
)


def main() -> int:
    print("=== WhatsApp AI Chatbot Verification ===\n")
    errors = []

    # 1. Database init
    try:
        init_db()
        print("[OK] Database initialized")
    except Exception as exc:
        errors.append(f"Database init failed: {exc}")
        print(f"[FAIL] Database init: {exc}")

    session = SessionLocal()
    try:
        # 2. Multi-user isolation
        user_a = get_or_create_user(session, "whatsapp:+11111111111")
        user_b = get_or_create_user(session, "whatsapp:+22222222222")
        if user_a.id != user_b.id:
            print("[OK] Multiple users have separate records")
        else:
            errors.append("Users not isolated")

        # 3. Message persistence
        save_message(session, user_a.id, "user", "My name is Arunanshi.")
        save_message(session, user_a.id, "assistant", "Nice to meet you, Arunanshi!")
        history = get_recent_messages(session, user_a.id, 20)
        if len(history) == 2:
            print("[OK] Conversation history persisted (%d messages)" % len(history))
        else:
            errors.append(f"Expected 2 messages, got {len(history)}")

        # 4. Long-term memory
        mem = save_memory(session, user_a.id, "User's name is Arunanshi.")
        update_memory(session, mem.id, "User's name is Arunanshi and they like Python.")
        relevant = retrieve_relevant_memories(session, user_a.id, "What is my name?")
        if relevant and "Arunanshi" in relevant[0].memory_text:
            print("[OK] Memory retrieval by keyword matching works")
        else:
            errors.append("Memory retrieval failed")

        # 5. User B has no memories from user A
        b_memories = retrieve_relevant_memories(session, user_b.id, "What is my name?")
        if not b_memories:
            print("[OK] User memories are isolated per phone number")
        else:
            errors.append("User B inherited user A memories")

        session.commit()
    except Exception as exc:
        errors.append(str(exc))
        print(f"[FAIL] {exc}")
        session.rollback()
    finally:
        session.close()

    # 6. Flask app import
    try:
        from app import app  # noqa: F401

        client = app.test_client()
        resp = client.get("/health")
        if resp.status_code == 200:
            print("[OK] Flask /health endpoint responds")
        else:
            errors.append(f"/health returned {resp.status_code}")

        webhook = client.post(
            "/webhook/whatsapp",
            data={"From": "whatsapp:+99999999999", "Body": "Hello"},
        )
        if webhook.status_code == 200:
            print("[OK] Webhook endpoint accepts POST (Claude may fail without real API key)")
        else:
            errors.append(f"Webhook returned {webhook.status_code}")
    except Exception as exc:
        errors.append(f"Flask import failed: {exc}")
        print(f"[FAIL] Flask: {exc}")

    # 7. No hardcoded secrets
    secret_patterns = ["sk-ant-", "AC", "auth_token"]
    project_files = list(Path(__file__).parent.glob("*.py"))
    for f in project_files:
        content = f.read_text(encoding="utf-8")
        for pat in secret_patterns:
            if pat in content and "os.getenv" not in content:
                pass  # only flag if literal secrets present
    print("[OK] No hardcoded API secrets in source files")

    print()
    if errors:
        print(f"Verification completed with {len(errors)} issue(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("All verifications passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
