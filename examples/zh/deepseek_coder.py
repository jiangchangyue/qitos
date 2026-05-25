"""DeepSeek 编码 Agent 示例 — 使用 DeepSeek Chat 模型。

运行方式：
    DEEPSEEK_API_KEY=your-key python deepseek_coder.py

功能：
    - 代码生成和分析
    - JSON Decision 协议
    - CompactHistory 长对话管理
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, List

from qitos.core.agent_module import AgentModule
from qitos.core.state import StateSchema
from qitos.engine.engine import Engine
from qitos.kit.history.compact_history import compact_history
from qitos.models.openai_compatible import OpenAICompatibleModel


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass
class DeepSeekCoderState(StateSchema):
    """DeepSeek 编码 Agent 状态。"""

    code_output: str = ""
    error_messages: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class DeepSeekCoderAgent(AgentModule[DeepSeekCoderState, Any, Any]):
    """DeepSeek 代码生成助手。"""

    def init_state(self, task: str, **kwargs: Any) -> DeepSeekCoderState:
        return DeepSeekCoderState(task=task, max_steps=30)

    def build_system_prompt(self, state: DeepSeekCoderState) -> str:
        return (
            "你是一个专业的编程助手，擅长代码生成、分析和调试。\n"
            "请根据用户需求生成高质量的代码，并提供清晰的解释。\n"
            f"任务：{state.task}"
        )

    def prepare(self, state: DeepSeekCoderState) -> dict[str, Any]:
        return {}

    def reduce(
        self,
        state: DeepSeekCoderState,
        decision: Any,
        results: list[Any],
    ) -> DeepSeekCoderState:
        if results:
            result_str = str(results[-1])
            if "error" in result_str.lower():
                state.error_messages.append(result_str[:500])
            else:
                state.code_output = result_str[:5000]
        return state


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("请设置 DEEPSEEK_API_KEY 环境变量")
        return

    # 配置模型
    model = OpenAICompatibleModel(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )

    # 配置 CompactHistory（长对话场景）
    history = compact_history(
        max_tokens=32000,
        keep_last_rounds=3,
        auto_compact=True,
    )

    # 创建 Agent 并运行
    agent = DeepSeekCoderAgent()
    engine = Engine(agent=agent, model=model, history=history)

    result = engine.run("写一个 Python 快速排序函数，并添加类型注解和文档字符串")
    print(f"\n代码输出：\n{result.state.code_output}")


if __name__ == "__main__":
    main()
