"""Google Gemini API client — free tier, no credit card required."""

import logging

import google.generativeai as genai

from config import Config, get_system_prompt
from memory import parse_memory_extraction_response
from models import Message

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper around Google Gemini for conversational AI."""

    def __init__(self) -> None:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model_name = Config.GEMINI_MODEL

    def _build_contents(
        self,
        history: list[Message],
        current_message: str,
        memories: list[str],
    ) -> list[dict]:
        """Build Gemini chat history including memories as context."""
        contents: list[dict] = []

        if memories:
            memory_block = (
                "Important facts to remember about this user:\n"
                + "\n".join(f"- {m}" for m in memories)
            )
            contents.append({"role": "user", "parts": [memory_block]})
            contents.append(
                {
                    "role": "model",
                    "parts": ["Understood. I will use these facts to personalize my replies."],
                }
            )

        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [msg.content]})

        contents.append({"role": "user", "parts": [current_message]})
        return contents

    def generate_reply(
        self,
        history: list[Message],
        current_message: str,
        memories: list[str],
    ) -> str:
        """Send conversation context to Gemini and return the reply."""
        system_prompt = get_system_prompt()
        contents = self._build_contents(history, current_message, memories)

        logger.info(
            "Gemini request: model=%s, history=%d, memories=%d, message_len=%d",
            self.model_name,
            len(history),
            len(memories),
            len(current_message),
        )

        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )

        # Use chat for multi-turn; single turn if no prior context blocks
        if len(contents) > 1:
            prior = contents[:-1]
            last = contents[-1]["parts"][0]
            chat = model.start_chat(history=prior)
            response = chat.send_message(last)
        else:
            response = model.generate_content(current_message)

        reply = (response.text or "").strip()
        logger.info("Gemini response: len=%d", len(reply))
        return reply

    def extract_memories(self, user_message: str, assistant_reply: str) -> list[str]:
        """Ask Gemini to extract durable facts from an exchange."""
        extraction_prompt = (
            "Extract important long-term facts about the user from this exchange. "
            "Return ONLY a JSON array of strings, e.g. [\"User's name is Arun.\"]. "
            "Return [] if nothing worth remembering.\n\n"
            f"User: {user_message}\nAssistant: {assistant_reply}"
        )

        try:
            model = genai.GenerativeModel(model_name=self.model_name)
            response = model.generate_content(extraction_prompt)
            raw = (response.text or "").strip()
            facts = parse_memory_extraction_response(raw)
            logger.info("Extracted %d memory candidates", len(facts))
            return facts
        except Exception:
            logger.exception("Gemini memory extraction failed")
            return []
