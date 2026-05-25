"""法律咨询 Agent 示例 — 使用 Qwen + DashScope。

运行方式：
    DASHSCOPE_API_KEY=your-key python legal_consulting_agent.py

功能：
    - 向量检索法律法规
    - 自动添加免责声明
    - 多轮对话支持
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

from qitos.core.agent_module import AgentModule
from qitos.core.state import StateSchema
from qitos.engine.critic_decorator import critic
from qitos.engine.engine import Engine
from qitos.kit.embedding import DashScopeEmbedder
from qitos.kit.memory import VectorMemory
from qitos.models.openai_compatible import OpenAICompatibleModel


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass
class LegalConsultState(StateSchema):
    """法律咨询 Agent 状态。"""

    query: str = ""
    relevant_articles: List[Dict] = field(default_factory=list)
    legal_analysis: str = ""
    disclaimer_added: bool = False


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class LegalConsultAgent(AgentModule[LegalConsultState, Any, Any]):
    """中文法律咨询助手。"""

    def init_state(self, task: str, **kwargs: Any) -> LegalConsultState:
        return LegalConsultState(task=task, max_steps=15)

    def build_system_prompt(self, state: LegalConsultState) -> str:
        return (
            "你是一个专业的法律咨询助手。你的职责是：\n"
            "1. 根据用户问题检索相关法律条文\n"
            "2. 提供客观的法律分析\n"
            "3. 在回答末尾添加免责声明\n"
            "注意：你不能提供具体法律建议，只能提供法律信息参考。\n"
            f"用户问题：{state.task}"
        )

    def prepare(self, state: LegalConsultState) -> dict[str, Any]:
        return {}

    def reduce(
        self,
        state: LegalConsultState,
        decision: Any,
        results: list[Any],
    ) -> LegalConsultState:
        if results:
            state.legal_analysis = str(results[-1])[:2000]
        return state


# ---------------------------------------------------------------------------
# Critic: 强制添加免责声明
# ---------------------------------------------------------------------------


@critic(name="legal_disclaimer", score=0.8)
def legal_disclaimer_critic(state: Any, decision: Any, results: list) -> str:
    """确保法律咨询回答包含免责声明。"""
    if state.disclaimer_added:
        return "continue"
    # 检查回答中是否已包含免责声明
    analysis = getattr(state, "legal_analysis", "")
    if "仅供参考" in analysis and "不构成法律建议" in analysis:
        state.disclaimer_added = True
        return "continue"
    return (
        "retry",
        "回答缺少免责声明",
        "重要：你必须在回答末尾添加以下免责声明：\n"
        "\"以上内容仅供参考，不构成法律建议。如需专业法律意见，请咨询持证律师。\"",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("请设置 DASHSCOPE_API_KEY 环境变量")
        return

    # 配置向量知识库
    embedder = DashScopeEmbedder(model="text-embedding-v3", api_key=api_key)
    knowledge = VectorMemory(embedder=embedder, top_k=5)

    # 索引示例法律条文
    articles = [
        {"content": "《民法典》第一千一百六十五条：行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。"},
        {"content": "《劳动合同法》第三十六条：用人单位与劳动者协商一致，可以解除劳动合同。"},
        {"content": "《劳动合同法》第三十九条：劳动者有下列情形之一的，用人单位可以解除劳动合同："
                    "(一)在试用期间被证明不符合录用条件的；(二)严重违反用人单位的规章制度的。"},
    ]
    for article in articles:
        knowledge.append(article)

    # 配置模型
    model = OpenAICompatibleModel(
        model="qwen-plus",
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    # 创建 Agent 并运行
    agent = LegalConsultAgent()
    engine = Engine(agent=agent, model=model)
    engine.add_critic(legal_disclaimer_critic)

    result = engine.run("劳动合同解除有哪些法定情形？")
    print(f"\n分析结果：\n{result.state.legal_analysis}")


if __name__ == "__main__":
    main()
