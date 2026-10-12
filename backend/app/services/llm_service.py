import json
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings

class LLMService:
    """Multi-provider LLM adapter supporting OpenAI-compatible, Anthropic, Gemini, and Ollama."""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    def _redact_error(self, message: str) -> str:
        """Strip sensitive credentials and token patterns from error logs and responses."""
        if self.api_key and len(self.api_key) > 4:
            message = message.replace(self.api_key, "[REDACTED_API_KEY]")
        return message

    def is_configured(self) -> bool:
        """Check if server-side operator has configured an LLM credential."""
        return bool(self.api_key and self.api_key.strip())

    async def generate_remediation_advisory(self, scorecard_data: Dict[str, Any]) -> str:
        """Opt-in advisory recommendations grounded in actual scorecard data."""
        if not self.is_configured():
            return "Advisory LLM is not configured by operator. Deterministic remediation playbook is active."

        prompt = (
            f"Review this data quality audit scorecard for a machine learning tabular dataset:\n"
            f"- Overall Score: {scorecard_data.get('overall_score')}\n"
            f"- Letter Grade: {scorecard_data.get('grade')}\n"
            f"- Completeness null rates: {json.dumps(scorecard_data.get('completeness', []))}\n"
            f"- Duplicates: {scorecard_data.get('duplicates_count')}\n"
            f"- Statistical Anomalies: {json.dumps(scorecard_data.get('anomalies', []))}\n"
            f"- Detected PII: {json.dumps(scorecard_data.get('pii_findings', []))}\n\n"
            "Provide concise, prioritized advisory engineering recommendations for mitigating downstream ML dataset skew. "
            "Address label noise, feature imputation strategies, and compliance risks. Be concrete and grounded in the findings above."
        )

        return await self._call_provider(
            system_prompt="You are an expert ML Data Platform Engineer providing advisory data remediation guidance.",
            user_prompt=prompt,
        )

    async def generate_drift_advisory(self, drift_data: Dict[str, Any]) -> str:
        """Opt-in advisory explanation for detected schema and distribution drift."""
        if not self.is_configured():
            return "Advisory LLM is not configured by operator. Statistical drift metrics are calculated offline."

        prompt = (
            f"Review the dataset drift comparison:\n"
            f"- Added columns: {drift_data.get('added_columns', [])}\n"
            f"- Removed columns: {drift_data.get('removed_columns', [])}\n"
            f"- Feature shifts: {json.dumps(drift_data.get('drifts', []))}\n"
            f"- Overall Drift Score: {drift_data.get('drift_score')}\n\n"
            "Diagnose whether this shift reflects expected business seasonality, upstream telemetry breakage, or feature drift that could degrade trained ML models. Provide validation steps."
        )

        return await self._call_provider(
            system_prompt="You are a Machine Learning Data Reliability Engineer analyzing feature and schema drift.",
            user_prompt=prompt,
        )

    async def _call_provider(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured():
            raise ValueError("LLM_API_KEY is not configured by operator. Use deterministic offline analysis.")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.provider == "anthropic":
                    return await self._call_anthropic(client, system_prompt, user_prompt)
                elif self.provider == "gemini":
                    return await self._call_gemini(client, system_prompt, user_prompt)
                elif self.provider == "ollama":
                    return await self._call_ollama(client, system_prompt, user_prompt)
                else:  # default openai-compatible (LiteLLM, OpenRouter, vLLM, OpenAI)
                    return await self._call_openai(client, system_prompt, user_prompt)
        except Exception as exc:
            redacted = self._redact_error(str(exc))
            raise RuntimeError(f"LLM provider '{self.provider}' call failed: {redacted}") from None

    async def _call_openai(self, client: httpx.AsyncClient, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        url = f"{self.base_url}/chat/completions"
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, client: httpx.AsyncClient, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model or "claude-3-5-sonnet-20241022",
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 1024,
            "temperature": 0.2,
        }
        url = f"{self.base_url}/v1/messages"
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]

    async def _call_gemini(self, client: httpx.AsyncClient, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return "No advisory response generated by Gemini."

    async def _call_ollama(self, client: httpx.AsyncClient, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model or "llama3",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
