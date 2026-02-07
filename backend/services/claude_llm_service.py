"""
Claude LLM Service - Anthropic API wrapper for Deep Insights feature flag.
Same chat() signature as LLMService so agents can use either interchangeably.
"""
import anthropic
from typing import Optional, List, Dict
from config import settings


class ClaudeLLMService:
    """Anthropic Claude API wrapper with the same interface as LLMService."""

    def __init__(self):
        self.model = "claude-sonnet-4-5-20250929"
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                timeout=120.0,
            )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a chat completion request to Claude.

        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system: System prompt
            temperature: Creativity (0-1)
            max_tokens: Max response length

        Returns:
            The assistant's response text
        """
        client = self._get_client()

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text

    def is_available(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(settings.ANTHROPIC_API_KEY)


# Singleton instance
claude_llm_service = ClaudeLLMService()
