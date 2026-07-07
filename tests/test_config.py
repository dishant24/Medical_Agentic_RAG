import pytest
from pydantic import ValidationError

from medrag.config import Settings


def test_settings_loads_groq_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    settings = Settings(_env_file=None)
    assert settings.groq_api_key == "test-key-123"


def test_settings_defaults_app_env_to_development(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"


def test_settings_raises_when_groq_api_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
