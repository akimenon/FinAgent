"""
LLM Service - Unified interface for Ollama/Qwen
Provides OpenAI-compatible API calls to local Ollama server
"""
import httpx
from typing import Optional, List, Dict, Any
from config import settings


class LLMService:
    """
    Service for interacting with Ollama running local LLMs.
    Uses OpenAI-compatible API format.
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=300.0)  # 5 min for complex synthesis
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Send a chat completion request to Ollama.

        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system: System prompt
            temperature: Creativity (0-1)
            max_tokens: Max response length

        Returns:
            The assistant's response text
        """
        client = self._get_client()

        # Build messages array with system prompt
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = client.post(
            f"{self.base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()

        result = response.json()
        return result.get("message", {}).get("content", "")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Simple generate endpoint (non-chat format).
        """
        client = self._get_client()

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = client.post(
            f"{self.base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()

        result = response.json()
        return result.get("response", "")

    def is_available(self) -> bool:
        """Check if Ollama server is running and model is available."""
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check if our model is available (with or without :latest tag)
                return any(self.model in name or name in self.model for name in model_names)
            return False
        except Exception:
            return False

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


# Singleton instance
llm_service = LLMService()
