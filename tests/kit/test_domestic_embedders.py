"""Tests for domestic (Chinese) model embedders — DashScope and Zhipu."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from qitos.kit.embedding import DashScopeEmbedder, ZhipuEmbedder, Embedder


# ---------------------------------------------------------------------------
# DashScopeEmbedder
# ---------------------------------------------------------------------------


class TestDashScopeEmbedder:
    def test_is_embedder(self):
        e = DashScopeEmbedder(api_key="test")
        assert isinstance(e, Embedder)

    def test_default_model(self):
        e = DashScopeEmbedder(api_key="test")
        assert e.model == "text-embedding-v3"

    def test_default_dimension(self):
        e = DashScopeEmbedder(api_key="test")
        assert e.dimension == 1024

    def test_custom_dimension(self):
        e = DashScopeEmbedder(api_key="test", dimensions=512)
        assert e.dimension == 512

    def test_v2_dimension(self):
        e = DashScopeEmbedder(model="text-embedding-v2", api_key="test")
        assert e.dimension == 1536

    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": "env-key"}):
            e = DashScopeEmbedder()
            assert e._api_key == "env-key"

    def test_api_key_explicit_overrides_env(self):
        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": "env-key"}):
            e = DashScopeEmbedder(api_key="explicit")
            assert e._api_key == "explicit"

    def test_embed_calls_client(self):
        e = DashScopeEmbedder(api_key="test")
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        e._client = mock_client

        result = e.embed("hello world")
        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-v3", input="hello world"
        )

    def test_embed_with_dimensions(self):
        e = DashScopeEmbedder(api_key="test", dimensions=512)
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 512)]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        e._client = mock_client

        e.embed("test")
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-v3", input="test", dimensions=512
        )

    def test_embed_batch(self):
        e = DashScopeEmbedder(api_key="test")
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4]),
        ]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        e._client = mock_client

        result = e.embed_batch(["hello", "world"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-v3", input=["hello", "world"]
        )

    def test_client_uses_dashscope_base_url(self):
        e = DashScopeEmbedder(api_key="test")
        mock_openai_cls = MagicMock()
        with patch("openai.OpenAI", mock_openai_cls):
            e._get_client()
            mock_openai_cls.assert_called_once_with(
                api_key="test",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

    def test_client_lazy_init(self):
        e = DashScopeEmbedder(api_key="test")
        assert e._client is None
        mock_openai_cls = MagicMock()
        with patch("openai.OpenAI", mock_openai_cls):
            e._get_client()
            assert e._client is not None
            # Second call reuses client
            e._get_client()

    def test_import_error_without_openai(self):
        e = DashScopeEmbedder(api_key="test")
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai package"):
                e._get_client()


# ---------------------------------------------------------------------------
# ZhipuEmbedder
# ---------------------------------------------------------------------------


class TestZhipuEmbedder:
    def test_is_embedder(self):
        e = ZhipuEmbedder(api_key="test")
        assert isinstance(e, Embedder)

    def test_default_model(self):
        e = ZhipuEmbedder(api_key="test")
        assert e.model == "embedding-3"

    def test_default_dimension(self):
        e = ZhipuEmbedder(api_key="test")
        assert e.dimension == 2048

    def test_custom_dimension(self):
        e = ZhipuEmbedder(api_key="test", dimensions=512)
        assert e.dimension == 512

    def test_v2_dimension(self):
        e = ZhipuEmbedder(model="embedding-2", api_key="test")
        assert e.dimension == 1024

    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"ZHIPU_API_KEY": "env-key"}):
            e = ZhipuEmbedder()
            assert e._api_key == "env-key"

    def test_api_key_explicit_overrides_env(self):
        with patch.dict("os.environ", {"ZHIPU_API_KEY": "env-key"}):
            e = ZhipuEmbedder(api_key="explicit")
            assert e._api_key == "explicit"

    def test_embed_calls_client(self):
        e = ZhipuEmbedder(api_key="test")
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        e._client = mock_client

        result = e.embed("hello world")
        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once_with(
            model="embedding-3", input="hello world"
        )

    def test_embed_with_dimensions(self):
        e = ZhipuEmbedder(api_key="test", dimensions=1024)
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1024)]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        e._client = mock_client

        e.embed("test")
        mock_client.embeddings.create.assert_called_once_with(
            model="embedding-3", input="test", dimensions=1024
        )

    def test_embed_batch(self):
        e = ZhipuEmbedder(api_key="test")
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4]),
        ]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        e._client = mock_client

        result = e.embed_batch(["hello", "world"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_client_uses_zhipu_base_url(self):
        e = ZhipuEmbedder(api_key="test")
        mock_openai_cls = MagicMock()
        with patch("openai.OpenAI", mock_openai_cls):
            e._get_client()
            mock_openai_cls.assert_called_once_with(
                api_key="test",
                base_url="https://open.bigmodel.cn/api/paas/v4",
            )

    def test_client_lazy_init(self):
        e = ZhipuEmbedder(api_key="test")
        assert e._client is None
        mock_openai_cls = MagicMock()
        with patch("openai.OpenAI", mock_openai_cls):
            e._get_client()
            assert e._client is not None

    def test_import_error_without_openai(self):
        e = ZhipuEmbedder(api_key="test")
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai package"):
                e._get_client()


# ---------------------------------------------------------------------------
# Interop: embedders work with VectorMemory
# ---------------------------------------------------------------------------


class TestEmbedderVectorMemoryInterop:
    def test_dashscope_with_vector_memory(self):
        from qitos.kit.memory.vector_memory import VectorMemory
        from qitos.core.memory import MemoryRecord

        embedder = DashScopeEmbedder(api_key="test")
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1024)]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        embedder._client = mock_client

        mem = VectorMemory(embedder=embedder)
        record = MemoryRecord(role="user", content="test query", step_id=0)
        mem.append(record)
        results = mem.retrieve({"text": "test query"})
        assert len(results) > 0

    def test_zhipu_with_vector_memory(self):
        from qitos.kit.memory.vector_memory import VectorMemory
        from qitos.core.memory import MemoryRecord

        embedder = ZhipuEmbedder(api_key="test")
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 2048)]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        embedder._client = mock_client

        mem = VectorMemory(embedder=embedder)
        record = MemoryRecord(role="user", content="test query", step_id=0)
        mem.append(record)
        results = mem.retrieve({"text": "test query"})
        assert len(results) > 0
