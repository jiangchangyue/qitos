"""向量嵌入 + 向量记忆 模式示例

演示使用 DashScopeEmbedder / ZhipuEmbedder 配合 VectorMemory，
实现基于语义相似度的记忆存储与检索。

本示例使用模拟嵌入器，无需真实 API 密钥即可运行。
如需实际语义搜索，请替换为真实的嵌入器。
"""

from qitos.core.memory import MemoryRecord
from qitos.kit.memory.vector_memory import VectorMemory
from qitos.kit.embedding.dashscope_embedding import DashScopeEmbedder
from qitos.kit.embedding.zhipu_embedding import ZhipuEmbedder


# --- 方案 A：使用模拟嵌入器（无需 API 密钥）---------------------------------

# 使用内置的哈希嵌入器，可离线运行
from qitos.kit.memory.vector_memory import _HashEmbedder  # noqa: E402

offline_embedder = _HashEmbedder()

memory = VectorMemory(embedder=offline_embedder)

# 存储记录
memory.append(MemoryRecord(
    role="user",
    content="如何在阿里云上部署 Python Web 应用？",
    step_id=1,
    metadata={"topic": "部署"},
))
memory.append(MemoryRecord(
    role="assistant",
    content="可以使用容器服务或函数计算进行无服务器部署。",
    step_id=2,
    metadata={"topic": "部署"},
))
memory.append(MemoryRecord(
    role="user",
    content="RAG 流水线用什么向量数据库最好？",
    step_id=3,
    metadata={"topic": "向量数据库"},
))

# 按查询检索
results = memory.retrieve(query={"text": "部署 Web 应用"})
print(f"查询 '部署 Web 应用' 找到 {len(results)} 条结果：")
for r in results:
    print(f"  - [{r.metadata.get('topic')}] {r.content[:80]}")

# 摘要
print(f"\n记忆摘要：\n{memory.summarize()}")


# --- 方案 B：使用真实 API（需要 API 密钥）------------------------------------
#
# from qitos.kit.embedding.dashscope_embedding import DashScopeEmbedder
# from qitos.kit.embedding.zhipu_embedding import ZhipuEmbedder
#
# # DashScope（阿里云灵积）
# embedder = DashScopeEmbedder(model="text-embedding-v3", api_key="sk-你的密钥")
#
# # 智谱 AI（BigModel）
# # embedder = ZhipuEmbedder(model="embedding-3", api_key="你的智谱密钥")
#
# memory = VectorMemory(embedder=embedder)
# memory.append(MemoryRecord(role="user", content="你好世界", step_id=1))
# results = memory.retrieve(query={"text": "问候"})
