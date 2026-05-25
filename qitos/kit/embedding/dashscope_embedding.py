"""DashScope embedding adapter (Alibaba Cloud).

Uses the OpenAI-compatible endpoint provided by DashScope,
so the implementation mirrors OpenAIEmbedder with DashScope defaults.

Supported models:
- ``text-embedding-v3`` (default, 1024-dim)
- ``text-embedding-v2`` (1536-dim)
- ``text-embedding-v1`` (1536-dim)
"""

from __future__ import annotations

import os
from typing import List, Optional

from .base import Embedder

_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

_DASHSCOPE_DIMENSIONS = {
    "text-embedding-v3": 1024,
    "text-embedding-v2": 1536,
    "text-embedding-v1": 1536,
}


class DashScopeEmbedder(Embedder):
    """Embedder backed by the DashScope (Alibaba Cloud) API.

    Parameters
    ----------
    model : str
        Model name (default: ``text-embedding-v3``).
    api_key : str | None
        DashScope API key. Falls back to ``DASHSCOPE_API_KEY`` env var.
    dimensions : int | None
        Override output dimensions (v3 supports 512/768/1024).
    """

    def __init__(
        self,
        model: str = "text-embedding-v3",
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        self.model = model
        self._api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        self._dimensions = dimensions
        self._client = None

    @property
    def dimension(self) -> int:
        if self._dimensions:
            return self._dimensions
        return _DASHSCOPE_DIMENSIONS.get(self.model, 1024)

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package is required for DashScopeEmbedder. "
                    "Install with: pip install openai"
                )
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=_DASHSCOPE_BASE_URL,
            )
        return self._client

    def embed(self, text: str) -> List[float]:
        client = self._get_client()
        kwargs: dict = {"model": self.model, "input": text}
        if self._dimensions:
            kwargs["dimensions"] = self._dimensions
        response = client.embeddings.create(**kwargs)
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        kwargs: dict = {"model": self.model, "input": texts}
        if self._dimensions:
            kwargs["dimensions"] = self._dimensions
        response = client.embeddings.create(**kwargs)
        return [item.embedding for item in response.data]


__all__ = ["DashScopeEmbedder"]
