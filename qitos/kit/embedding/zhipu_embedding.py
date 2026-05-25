"""Zhipu AI embedding adapter.

Uses the OpenAI-compatible endpoint provided by Zhipu AI (BigModel),
so the implementation mirrors OpenAIEmbedder with Zhipu defaults.

Supported models:
- ``embedding-3`` (default, 2048-dim)
- ``embedding-2`` (1024-dim)
"""

from __future__ import annotations

import os
from typing import List, Optional

from .base import Embedder

_ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

_ZHIPU_DIMENSIONS = {
    "embedding-3": 2048,
    "embedding-2": 1024,
}


class ZhipuEmbedder(Embedder):
    """Embedder backed by the Zhipu AI (BigModel) API.

    Parameters
    ----------
    model : str
        Model name (default: ``embedding-3``).
    api_key : str | None
        Zhipu API key. Falls back to ``ZHIPU_API_KEY`` env var.
    dimensions : int | None
        Override output dimensions.
    """

    def __init__(
        self,
        model: str = "embedding-3",
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        self.model = model
        self._api_key = api_key or os.environ.get("ZHIPU_API_KEY", "")
        self._dimensions = dimensions
        self._client = None

    @property
    def dimension(self) -> int:
        if self._dimensions:
            return self._dimensions
        return _ZHIPU_DIMENSIONS.get(self.model, 2048)

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package is required for ZhipuEmbedder. "
                    "Install with: pip install openai"
                )
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=_ZHIPU_BASE_URL,
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


__all__ = ["ZhipuEmbedder"]
