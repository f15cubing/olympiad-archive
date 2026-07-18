import pytest

from ai_tagging.gemini_client import GeminiClient


def test_gemini_client_requires_key(monkeypatch):
    """Client initialization should raise ValueError without API key."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        GeminiClient()


def test_gemini_client_accepts_env_key(monkeypatch):
    """If GEMINI_API_KEY is set, client should initialize without error."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    client = GeminiClient()
    assert client is not None
    # Should have either client.client or client.model attribute
    assert hasattr(client, "rate_limiter")
