"""Tests for config security — API key masking and tracing redaction."""
from __future__ import annotations

from qitos.config.loader import ModelConfig
from qitos.tracing.config import _REDACTED_FIELDS, _REDACTED_MARKER, _redact_dict


def test_model_config_to_dict_masks_api_key():
    """ModelConfig.to_dict() masks non-empty api_key."""
    cfg = ModelConfig(api_key="sk-12345-secret")
    d = cfg.to_dict()
    assert d["api_key"] == "***REDACTED***"


def test_model_config_to_dict_empty_api_key():
    """ModelConfig.to_dict() returns empty string for empty api_key."""
    cfg = ModelConfig(api_key="")
    d = cfg.to_dict()
    assert d["api_key"] == ""


def test_model_config_preserves_other_fields():
    """Other fields are not affected by api_key masking."""
    cfg = ModelConfig(provider="anthropic", model="claude-3", api_key="sk-test")
    d = cfg.to_dict()
    assert d["provider"] == "anthropic"
    assert d["model"] == "claude-3"
    assert d["api_key"] == "***REDACTED***"


def test_redacted_fields_includes_sensitive_names():
    """_REDACTED_FIELDS includes common sensitive field names."""
    expected = {"api_key", "authorization", "token", "secret", "password",
                "access_token", "refresh_token", "private_key", "credentials"}
    assert expected.issubset(_REDACTED_FIELDS)


def test_redact_dict_masks_sensitive_fields():
    """_redact_dict replaces sensitive field values with the redaction marker."""
    data = {
        "tool_args": {"command": "ls"},
        "api_key": "sk-12345",
        "authorization": "Bearer abc",
        "safe_field": "visible",
    }
    result = _redact_dict(data)
    assert result["tool_args"] == _REDACTED_MARKER
    assert result["api_key"] == _REDACTED_MARKER
    assert result["authorization"] == _REDACTED_MARKER
    assert result["safe_field"] == "visible"


def test_redact_dict_handles_nested_dicts():
    """_redact_dict recursively redacts nested dicts."""
    data = {
        "outer": {
            "password": "secret123",
            "name": "test",
        }
    }
    result = _redact_dict(data)
    assert result["outer"]["password"] == _REDACTED_MARKER
    assert result["outer"]["name"] == "test"


def test_redact_dict_handles_lists_of_dicts():
    """_redact_dict recursively redacts dicts inside lists."""
    data = {
        "items": [
            {"token": "abc", "value": 1},
            {"token": "def", "value": 2},
        ]
    }
    result = _redact_dict(data)
    assert result["items"][0]["token"] == _REDACTED_MARKER
    assert result["items"][1]["token"] == _REDACTED_MARKER
    assert result["items"][0]["value"] == 1
