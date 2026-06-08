"""Anthropic Claude API client for chat and memory extraction."""

import logging
from typing import Any

import anthropic

from config import Config, get_system_prompt
from models import Message

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper around the Anthropic SDK for conversational AI."""

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = Config.CLAUDE_MODEL

    def build_messages(
        self,
        history: list[Message],
        current_message: str,
        memories: list[str],
    ) -> list[dict[str, Any]]:
        """
        Build the message list for Claude.

        Context order:
          System prompt (via system param)
          Relevant memories (injected as first user context block)
          Recent chat history
          Current message
        """
        messages: list[dict[str, Any]] = []

        if memories:
            memory_block = (
                "The following are important facts you remember about this user "
                "(from previous conversations):\n\n"
                + "\n".join(f"- {m}" for m in memories)
            )
            messages.append({"role": "user", "content": memory_block})
            messages.append(
                {
                    "role": "assistant",
                    "content": "Understood. I'll use these memories to personalize my responses.",
                }
            )

        for msg in history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})

        messages.append({"role": "user", "content": current_message})
        return messages

    def generate_reply(
        self,
        history: list[Message],
        current_message: str,
        memories: list[str],
    ) -> str:
        """Send conversation context to Claude and return the assistant reply."""
        messages = self.build_messages(history, current_message, memories)
        system_prompt = get_system_prompt()

        logger.info(
            "Claude request: model=%s, history=%d, memories=%d, message_len=%d",
            self.model,
            len(history),
            len(memories),
            len(current_message),
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )
        except anthropic.APIError:
            logger.exception("Claude API error")
            raise

        reply = ""
        for block in response.content:
            if hasattr(block, "text"):
                reply += block.text

        reply = reply.strip()
        logger.info("Claude response: len=%d", len(reply))
        return reply

    def extract_memories(self, user_message: str, assistant_reply: str) -> list[str]:
        """
        Ask Claude to extract durable facts worth remembering from an exchange.

        Returns a list of fact strings.
        """
        from memory import parse_memory_extraction_response

        extraction_prompt = (
            "Analyze the following conversation exchange and extract any important "
            "facts about the user that should be remembered long-term.\n\n"
            "Extract facts such as:\n"
            "- Name, age, location, occupation\n"
            "- Preferences, likes, dislikes\n"
            "- Important dates, relationships\n"
            "- Goals, projects, ongoing situations\n"
            "- Any explicit request to remember something\n\n"
            "Rules:\n"
            "- Only extract factual information the user shared or confirmed\n"
            "- Do NOT extract trivial greetings or small talk\n"
            "- Return ONLY a JSON array of strings, e.g. [\"User's name is Arun.\", \"User lives in London.\"]\n"
            "- Return an empty array [] if nothing worth remembering\n\n"
            f"User message: {user_message}\n\n"
            f"Assistant reply: {assistant_reply}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                system="You extract durable user facts for long-term memory. Respond only with a JSON array.",
                messages=[{"role": "user", "content": extraction_prompt}],
            )
            raw = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw += block.text
            facts = parse_memory_extraction_response(raw)
            logger.info("Extracted %d memory candidates", len(facts))
            return facts
        except Exception:
            logger.exception("Memory extraction API call failed")
            return []
