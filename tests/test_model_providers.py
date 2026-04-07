from __future__ import annotations

import os
import sys
from types import SimpleNamespace

from qitos.models import (
    AnthropicModel,
    GeminiModel,
    LiteLLMModel,
    LMStudioModel,
    ModelFactory,
    OllamaModel,
    infer_context_window,
)


class _FakeHTTPResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            error = requests.HTTPError(f"status={self.status_code}")
            error.response = self
            raise error


def test_anthropic_native_messages_adapter(monkeypatch) -> None:
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeHTTPResponse(
            {
                "content": [
                    {"type": "text", "text": "Final Answer: native anthropic works"}
                ],
                "usage": {
                    "input_tokens": 100,
                    "cache_read_input_tokens": 3,
                    "output_tokens": 22,
                },
            }
        )

    monkeypatch.setattr("qitos.models.anthropic.requests.post", fake_post)
    llm = AnthropicModel(api_key="anthropic-test", model="claude-test")
    out = llm(
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Say hello."},
        ]
    )

    assert out == "Final Answer: native anthropic works"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "anthropic-test"
    assert captured["json"]["system"] == "You are helpful."
    assert captured["json"]["messages"] == [{"role": "user", "content": "Say hello."}]
    assert llm.extract_usage() == {
        "prompt_tokens": 103,
        "completion_tokens": 22,
        "total_tokens": 125,
    }


def test_gemini_native_adapter(monkeypatch) -> None:
    captured = {}

    def fake_post(url, params=None, json=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["json"] = json
        return _FakeHTTPResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": 'Action: search(query="gemini")'},
                            ]
                        }
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 18,
                    "candidatesTokenCount": 7,
                    "totalTokenCount": 25,
                },
            }
        )

    monkeypatch.setattr("qitos.models.gemini.requests.post", fake_post)
    llm = GeminiModel(api_key="gemini-test", model="gemini-2.5-flash")
    out = llm(
        [
            {"role": "system", "content": "Follow protocol."},
            {"role": "user", "content": "Search for docs."},
            {"role": "assistant", "content": "Thinking."},
        ]
    )

    assert out == 'Action: search(query="gemini")'
    assert captured["params"] == {"key": "gemini-test"}
    assert (
        captured["json"]["systemInstruction"]["parts"][0]["text"] == "Follow protocol."
    )
    assert captured["json"]["contents"][0]["role"] == "user"
    assert captured["json"]["contents"][1]["role"] == "model"
    assert llm.extract_usage() == {
        "prompt_tokens": 18,
        "completion_tokens": 7,
        "total_tokens": 25,
    }


def test_litellm_adapter_and_usage(monkeypatch) -> None:
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return {
            "choices": [{"message": {"content": "Final Answer: litellm works"}}],
            "usage": {"prompt_tokens": 13, "completion_tokens": 5, "total_tokens": 18},
        }

    monkeypatch.setitem(
        sys.modules, "litellm", SimpleNamespace(completion=fake_completion)
    )
    llm = LiteLLMModel(model="anthropic/claude-3-5-sonnet-latest", api_key="lite-key")
    out = llm([{"role": "user", "content": "Say hi"}])

    assert out == "Final Answer: litellm works"
    assert captured["model"] == "anthropic/claude-3-5-sonnet-latest"
    assert captured["api_key"] == "lite-key"
    assert llm.extract_usage() == {
        "prompt_tokens": 13,
        "completion_tokens": 5,
        "total_tokens": 18,
    }


def test_model_factory_from_env_supports_new_providers(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("LM_STUDIO_BASE_URL", raising=False)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-env")
    llm = ModelFactory.from_env(model="claude-test")
    assert isinstance(llm, AnthropicModel)

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-env")
    llm = ModelFactory.from_env(model="gemini-test")
    assert isinstance(llm, GeminiModel)

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LITELLM_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("LITELLM_API_KEY", "lite-env")
    llm = ModelFactory.from_env()
    assert isinstance(llm, LiteLLMModel)
    assert llm.model == "openai/gpt-4o-mini"

    monkeypatch.setenv("QITOS_MODEL_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    llm = ModelFactory.from_env(model="llama3.1")
    assert isinstance(llm, OllamaModel)

    monkeypatch.setenv("QITOS_MODEL_PROVIDER", "lmstudio")
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    llm = ModelFactory.from_env(model="local-model")
    assert isinstance(llm, LMStudioModel)


def test_local_openai_compatible_like_parsing_supports_tool_calls() -> None:
    lmstudio = LMStudioModel(model="local-model")
    out = lmstudio._parse_response(
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "search",
                                    "arguments": '{"query": "lmstudio"}',
                                }
                            }
                        ]
                    }
                }
            ]
        }
    )
    assert out == 'Action: search(query="lmstudio")'

    ollama = OllamaModel(model="llama3.1")
    out = ollama._parse_response(
        {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "grep_files",
                            "arguments": {"pattern": "TODO"},
                        }
                    }
                ]
            }
        }
    )
    assert out == 'Action: grep_files(pattern="TODO")'


def test_context_registry_infers_anthropic_and_gemini_windows() -> None:
    assert infer_context_window("claude-3-5-sonnet-latest") == 200_000
    assert infer_context_window("gemini-2.5-flash") == 1_048_576


def test_explicit_provider_override_wins(monkeypatch) -> None:
    monkeypatch.setenv("QITOS_MODEL_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-env")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-env")
    llm = ModelFactory.from_env(model="claude-test")
    assert isinstance(llm, AnthropicModel)

    monkeypatch.setenv("QITOS_MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-env")
    llm = ModelFactory.from_env(model="gemini-test")
    assert isinstance(llm, GeminiModel)

    monkeypatch.delenv("QITOS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    for name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "LITELLM_MODEL",
        "LITELLM_API_KEY",
        "OLLAMA_HOST",
        "OLLAMA_BASE_URL",
        "LM_STUDIO_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    assert ModelFactory.from_env() is None
