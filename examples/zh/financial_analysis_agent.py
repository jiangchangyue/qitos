"""金融分析 Agent 示例 — 使用 GLM + 智谱向量。

运行方式：
    ZHIPU_API_KEY=your-key python financial_analysis_agent.py

功能：
    - 结构化金融数据分析
    - 风险审查和投资建议过滤
    - JSON 协议输出
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

from qitos.core.agent_module import AgentModule
from qitos.core.state import StateSchema
from qitos.engine.critic_decorator import critic
from qitos.engine.engine import Engine
from qitos.kit.embedding import ZhipuEmbedder
from qitos.kit.memory import VectorMemory
from qitos.models.openai_compatible import OpenAICompatibleModel


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass
class FinancialAnalysisState(StateSchema):
    """金融分析 Agent 状态。"""

    target_company: str = ""
    financial_data: Dict = field(default_factory=dict)
    analysis_results: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    disclaimer_added: bool = False


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class FinancialAnalysisAgent(AgentModule[FinancialAnalysisState, Any, Any]):
    """金融数据分析助手。"""

    def init_state(self, task: str, **kwargs: Any) -> FinancialAnalysisState:
        return FinancialAnalysisState(
            task=task,
            target_company=task,
            max_steps=20,
        )

    def build_system_prompt(self, state: FinancialAnalysisState) -> str:
        return (
            "你是一个专业的金融数据分析助手。\n"
            "你的职责是：\n"
            "1. 收集和分析目标公司的财务数据\n"
            "2. 识别关键风险因素\n"
            "3. 提供客观的数据分析报告\n"
            "注意：你不能提供投资建议，只能提供数据分析参考。\n"
            f"分析目标：{state.target_company}"
        )

    def prepare(self, state: FinancialAnalysisState) -> dict[str, Any]:
        return {}

    def reduce(
        self,
        state: FinancialAnalysisState,
        decision: Any,
        results: list[Any],
    ) -> FinancialAnalysisState:
        if results:
            state.analysis_results.append(str(results[-1])[:1000])
        return state


# ---------------------------------------------------------------------------
# Critic: 风险审查
# ---------------------------------------------------------------------------


@critic(name="financial_risk_guard", score=0.8)
def financial_risk_critic(state: Any, decision: Any, results: list) -> str:
    """过滤投资建议表述并确保包含风险提示。"""
    analysis_text = " ".join(getattr(state, "analysis_results", []))
    investment_keywords = ["建议买入", "推荐投资", "必涨", "稳赚"]

    for keyword in investment_keywords:
        if keyword in analysis_text:
            return (
                "retry",
                f"检测到投资建议倾向：{keyword}",
                "请修改：移除投资建议表述，只保留客观数据分析。"
                "在报告末尾添加风险提示和免责声明。",
            )

    if not getattr(state, "disclaimer_added", False):
        if "投资有风险" in analysis_text or "仅供参考" in analysis_text:
            state.disclaimer_added = True
            return "continue"
        return (
            "retry",
            "缺少风险提示",
            "请在分析报告末尾添加：\"本报告仅供参考，不构成投资建议。投资有风险，决策需谨慎。\"",
        )

    return "continue"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.environ.get("ZHIPU_API_KEY", "")
    if not api_key:
        print("请设置 ZHIPU_API_KEY 环境变量")
        return

    # 配置向量知识库
    embedder = ZhipuEmbedder(model="embedding-3", api_key=api_key)
    knowledge = VectorMemory(embedder=embedder, top_k=5)

    # 索引示例金融数据
    reports = [
        {"content": "某上市公司2024年年报：营收增长15.3%，净利润增长8.7%，资产负债率42.1%"},
        {"content": "某上市公司风险提示：市场竞争加剧，原材料价格波动，汇率风险"},
    ]
    for report in reports:
        knowledge.append(report)

    # 配置模型（使用 JSON Decision 协议）
    model = OpenAICompatibleModel(
        model="glm-4-flash",
        api_key=api_key,
        base_url="https://open.bigmodel.cn/api/paas/v4",
    )

    # 创建 Agent 并运行
    agent = FinancialAnalysisAgent()
    engine = Engine(agent=agent, model=model)
    engine.add_critic(financial_risk_critic)

    result = engine.run("某上市公司")
    print(f"\n分析结果：")
    for r in result.state.analysis_results:
        print(f"  - {r[:200]}")


if __name__ == "__main__":
    main()
