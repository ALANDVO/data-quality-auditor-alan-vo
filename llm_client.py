import os
import sys
import asyncio
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from app.services.llm_service import LLMService

class LLM:
    """Unified LLM client interface backed by multi-provider LLMService."""

    def __init__(self):
        self.service = LLMService()

    def generate(self, prompt: str, system: str = "You are a helpful AI assistant.") -> str:
        """Synchronously generate text using configured provider."""
        if not self.service.is_configured():
            return "Advisory LLM is not configured. Running in offline deterministic mode."
        try:
            return asyncio.run(self.service._call_provider(system_prompt=system, user_prompt=prompt))
        except Exception as exc:
            return f"LLM error: {exc}"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Chat completion helper."""
        system = "You are a helpful AI assistant."
        user_msgs = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            else:
                user_msgs.append(m.get("content", ""))
        user_prompt = "\n".join(user_msgs)
        return self.generate(user_prompt, system=system)
