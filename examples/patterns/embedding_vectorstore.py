"""Embedding + VectorMemory pattern example.

Demonstrates using DashScopeEmbedder / ZhipuEmbedder with VectorMemory
to store and retrieve records by semantic similarity.

This example uses a mock embedder so it runs without real API access.
Replace the mock with a real embedder to get actual semantic search.
"""

from qitos.core.memory import MemoryRecord
from qitos.kit.memory.vector_memory import VectorMemory
from qitos.kit.embedding.dashscope_embedding import DashScopeEmbedder
from qitos.kit.embedding.zhipu_embedding import ZhipuEmbedder


# --- Option A: Use a mock embedder (no API key needed) -----------------------

mock_embedder = DashScopeEmbedder(api_key="sk-mock-key")
# DashScopeEmbedder will try to call the API on .embed(), so for a truly
# offline demo we patch the embed method with a simple hash-based function.

from qitos.kit.memory.vector_memory import _HashEmbedder   # noqa: E402

offline_embedder = _HashEmbedder()

memory = VectorMemory(embedder=offline_embedder)

# Store some records
memory.append(MemoryRecord(
    role="user", content="How to deploy a Python web app on Alibaba Cloud?",
    step_id=1, metadata={"topic": "deployment"},
))
memory.append(MemoryRecord(
    role="assistant", content="Use Container Service or Function Compute for serverless.",
    step_id=2, metadata={"topic": "deployment"},
))
memory.append(MemoryRecord(
    role="user", content="What is the best vector database for RAG pipelines?",
    step_id=3, metadata={"topic": "vector-db"},
))

# Retrieve by query
results = memory.retrieve(query={"text": "deploy web app"})
print(f"Found {len(results)} results for 'deploy web app':")
for r in results:
    print(f"  - [{r.metadata.get('topic')}] {r.content[:80]}")

# Summarize
print(f"\nSummary:\n{memory.summarize()}")


# --- Option B: Real API usage (requires API key) -----------------------------
#
# from qitos.kit.embedding.dashscope_embedding import DashScopeEmbedder
# from qitos.kit.embedding.zhipu_embedding import ZhipuEmbedder
#
# # DashScope (Alibaba Cloud)
# embedder = DashScopeEmbedder(model="text-embedding-v3", api_key="sk-your-key")
#
# # Zhipu AI (BigModel)
# # embedder = ZhipuEmbedder(model="embedding-3", api_key="your-zhipu-key")
#
# memory = VectorMemory(embedder=embedder)
# memory.append(MemoryRecord(role="user", content="Hello world", step_id=1))
# results = memory.retrieve(query={"text": "greeting"})
