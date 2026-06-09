"""Diagnose your Claude API key. Run: python test_api_key.py"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()

print("=" * 50)
print("  Claude / API Key Diagnostic Tool")
print("=" * 50)
print(f"Provider setting: {provider}\n")

if provider != "anthropic":
    print("TIP: Set LLM_PROVIDER=anthropic in .env to use Claude.\n")

key = os.getenv("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")
model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6").strip()

# --- Format checks (no secret printed) ---
print("[1] Checking key format...")
if not key:
    print("    FAIL: ANTHROPIC_API_KEY is empty in .env")
    print("    FIX:  Open .env and paste your key after ANTHROPIC_API_KEY=")
    sys.exit(1)

print(f"    Key length: {len(key)} characters (expect ~95-110)")
print(f"    Starts with sk-ant-: {key.startswith('sk-ant-')}")

if not key.startswith("sk-ant-"):
    print("    FAIL: Key must start with sk-ant-")
    print("    FIX:  Get key from https://console.anthropic.com/settings/keys")
    print("          NOT from claude.ai chat — that is a different product.")
    sys.exit(1)

if key != os.getenv("ANTHROPIC_API_KEY", "").strip():
    print("    WARN: Key had extra spaces or quotes — already stripped for test.")

if " " in key or "\n" in key or "\r" in key:
    print("    FAIL: Key contains spaces or line breaks")
    print("    FIX:  Re-paste the key on one line with no spaces.")
    sys.exit(1)

if key.startswith("sk-ant-api03-") or key.startswith("sk-ant-"):
    print("    OK:   Key format looks valid.\n")
else:
    print("    WARN: Unusual key prefix — may still work.\n")

# --- Model check ---
print(f"[2] Model: {model}")
if "20250514" in model:
    print("    WARN: This model is deprecated. Use claude-sonnet-4-6 instead.\n")
else:
    print("    OK\n")

# --- API test ---
print("[3] Calling Anthropic API...")
try:
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=model,
        max_tokens=20,
        messages=[{"role": "user", "content": "Reply with only the word OK"}],
    )
    text = response.content[0].text.strip()
    print(f"    SUCCESS! Claude replied: {text!r}")
    print("\n" + "=" * 50)
    print("  Your API key works. Next: update Railway and test WhatsApp.")
    print("=" * 50)
except Exception as exc:
    err = str(exc)
    print(f"    FAIL: {type(exc).__name__}")
    print(f"    {err}\n")

    print("=" * 50)
    print("  What this error usually means:")
    print("=" * 50)

    if "401" in err or "authentication" in err.lower() or "x-api-key" in err.lower():
        print("""
  INVALID API KEY — the key itself is wrong or not active.

  Checklist:
  1. Key from https://console.anthropic.com/settings/keys (API console)
     NOT from claude.ai website login.

  2. Claim free credits (no card needed for starter):
     https://console.anthropic.com/settings/billing
     - Look for "Claim free credits" or verify phone number.

  3. Create a BRAND NEW key after claiming credits.
     Old keys created before account setup may not work.

  4. In .env, the line must look exactly like:
     ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
     (no quotes, no spaces before/after)

  5. On Railway, DELETE old ANTHROPIC_API_KEY variable,
     create a new one, paste fresh key, wait for redeploy.
""")
    elif "404" in err or "not_found" in err.lower():
        print(f"""
  MODEL NOT FOUND — "{model}" may be wrong.

  FIX: In .env set:
  CLAUDE_MODEL=claude-sonnet-4-6
  Or for cheaper free-tier testing:
  CLAUDE_MODEL=claude-haiku-4-5-20251001
""")
    elif "429" in err or "rate" in err.lower():
        print("\n  RATE LIMITED — wait a minute and try again.")
    elif "credit" in err.lower() or "balance" in err.lower() or "billing" in err.lower():
        print("""
  NO CREDITS — account has no API balance.

  FIX: Go to https://console.anthropic.com/settings/billing
  → Claim free starter credits (phone verification, no card).
""")
    else:
        print(f"\n  Unexpected error. Share this message for help:\n  {err}")

    sys.exit(1)
