"""LLM provider factory — supports Gemini (free) and Claude."""

from config import Config


def get_llm_client():
    """Return the configured LLM client."""
    if Config.LLM_PROVIDER == "gemini":
        from gemini_client import GeminiClient

        return GeminiClient()

    from claude_client import ClaudeClient

    return ClaudeClient()
