"""Embedding protocols and implementations for vector-based memory."""

from .base import Embedder
from .openai_embedding import OpenAIEmbedder
from .local_embedding import LocalEmbedder
from .dashscope_embedding import DashScopeEmbedder
from .zhipu_embedding import ZhipuEmbedder

__all__ = [
    "Embedder",
    "OpenAIEmbedder",
    "LocalEmbedder",
    "DashScopeEmbedder",
    "ZhipuEmbedder",
]
