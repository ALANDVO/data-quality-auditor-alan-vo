import pytest
import unittest.mock as mock
from app.services.llm_service import LLMService

@pytest.mark.asyncio
async def test_llm_unconfigured_fallback():
    # When LLM_API_KEY is None or empty, is_configured should return False
    service = LLMService()
    service.api_key = None
    assert not service.is_configured()
    advisory = await service.generate_remediation_advisory({"overall_score": 0.8})
    assert "not configured" in advisory

def test_llm_redaction_synthetic_token():
    # Runtime-generated synthetic test token to test redaction
    synthetic_key = "test_key_" + ("0" * 16)
    service = LLMService()
    service.api_key = synthetic_key
    error_msg = f"Connection error while sending to api with key {synthetic_key} timed out."
    redacted = service._redact_error(error_msg)
    assert synthetic_key not in redacted
    assert "[REDACTED_API_KEY]" in redacted

@pytest.mark.asyncio
async def test_llm_openai_mocked_call():
    service = LLMService()
    service.api_key = "test_key_" + ("0" * 16)
    service.provider = "openai-compatible"

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Prioritize imputing missing feature columns."}}]
    }
    mock_resp.raise_for_status = mock.MagicMock()

    with mock.patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await service._call_provider("System prompt", "User prompt")
        assert "Prioritize imputing" in res
