"""ReAct agent that self-manages skills through tool use.

This example demonstrates the natural skill workflow:

请先检查是否已安装 SkillHub 商店，若未安装，请根据
https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/skillhub.md
安装Skillhub商店，但是只安装CLI，然后安装github技能。

若已安装，则直接安装github技能。

The agent decides on its own to:
1. Check if SkillHub is installed (check_skill_hub tool)
2. If not, install the hub (install_skill_hub tool)
3. Install the requested skill (install_skill tool)
4. Then proceed with the task using the skill

Usage:
    export OPENAI_API_KEY="your-key"
    python examples/react_self_managing_skills.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

from qitos import (
    Action,
    AgentModule,
    Decision,
    Engine,
    EnvSpec,
    HistoryPolicy,
    StateSchema,
    Task,
    TaskBudget,
    ToolRegistry,
)
from qitos.kit.env import HostEnv
from qitos.kit.parser import ReActTextParser
from qitos.kit.skill import SkillRegistry, SkillInjector
from qitos.kit.tool import EditorToolSet, RunCommand
from qitos.kit.tool.skill_tools import SkillToolSet
from qitos.models import OpenAIModel
from qitos.render import ClaudeStyleHook


# Model credentials
API_URL = "https://mahamphppeqac958mk5cmc9ae5dpbhkh.openapi-qb-ai.sii.edu.cn/v1"
API_KEY = "CVuXZ/EHsJQMV2peuex0chkH+99/QaKq089fciMtqHo="
MODEL_NAME = "kimi_k2.5"

SKILLHUB_URL = "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/skillhub.md"


SYSTEM_PROMPT = """You are a helpful AI assistant that can manage your own capabilities.

You have access to Skill Management tools that let you:
1. Check what skills are installed (check_skill_hub, list_installed_skills)
2. Install new capabilities (install_skill_hub, install_skill)
3. Get information about skills (get_skill_info)

When a user asks you to use a specific capability:
- First check if you have the necessary skill installed
- If not, install the SkillHub first (CLI only, just the hub manifest)
- Then install the requested skill through the hub
- Then FOLLOW the skill's instructions to complete the task using standard tools

IMPORTANT: Skills are NOT tools you can call directly. Skills provide INSTRUCTIONS that guide you on how to use the standard editor and command tools to accomplish tasks.

You have standard tools: view, read_file, write_file, run_command, list_files, etc.
Read the skill instructions carefully and follow them to complete the task.

Output Format:
Thought: <your reasoning about what to do>
Action: <tool_name>(arg1="value1", arg2="value2")

When you have completed the task, provide a final answer using this format:
Final Answer: <your complete answer>

The Final Answer should summarize what you did and the results.
"""


@dataclass
class SelfManagingState(StateSchema):
    """State that tracks skills installed during the run."""
    scratchpad: List[str] = field(default_factory=list)
    installed_skills_during_run: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Ensure proper initialization
        if not hasattr(self, 'scratchpad'):
            self.scratchpad = []
        if not hasattr(self, 'installed_skills_during_run'):
            self.installed_skills_during_run = []


class SelfManagingSkillAgent(AgentModule[SelfManagingState, Dict[str, Any], Action]):
    """Agent that self-manages skill installation.

    This agent uses skill management tools to dynamically install
    capabilities as needed during task execution.
    """

    def __init__(self, llm: Any, skillhub_url: str):
        # Shared skill registry between agent and tools
        self.skill_registry = SkillRegistry()
        self.skillhub_url = skillhub_url

        # Create tool registry
        tool_registry = ToolRegistry()

        # Add standard tools
        tool_registry.include(EditorToolSet())
        tool_registry.register(RunCommand())

        # Add skill management tools (shared registry!)
        skill_tools = SkillToolSet(self.skill_registry)
        tool_registry.register_toolset(skill_tools)

        super().__init__(
            tool_registry=tool_registry,
            llm=llm,
            model_parser=ReActTextParser()
        )

        self.skill_injector = SkillInjector()

    def init_state(self, task: str, **kwargs) -> SelfManagingState:
        return SelfManagingState(
            task=task,
            max_steps=kwargs.get("max_steps", 15)
        )

    def build_system_prompt(self, state: SelfManagingState) -> str:
        # Build base prompt
        parts = [SYSTEM_PROMPT]

        # Inject all available skills from the registry
        all_skills = self.skill_registry.list_skills()
        if all_skills:
            parts.append("\n\n# AVAILABLE SKILLS\n")
            parts.append("You have access to the following skills. Use their instructions when appropriate.\n")
            for skill in all_skills:
                parts.append(f"\n## {skill.name}")
                parts.append(skill.instructions[:800])
                parts.append("\n")

        # Inject any skills that were installed during this run (for skills added mid-run)
        if state.installed_skills_during_run:
            parts.append("\n\n# NEWLY INSTALLED SKILLS (this session)\n")
            for skill_name in state.installed_skills_during_run:
                skill = self.skill_registry.get(skill_name)
                if skill:
                    parts.append(f"\n## {skill.name}")
                    parts.append(skill.instructions[:800])

        return "".join(parts)

    def prepare(self, state: SelfManagingState) -> str:
        context = [
            f"Task: {state.task}",
            f"Step: {state.current_step}/{state.max_steps}",
            "\nYour task may involve skill management. Use the skill tools as needed.",
        ]

        # Show what skills are currently available
        skills = self.skill_registry.list_skills()
        if skills:
            context.append("\nCurrently installed skills:")
            for skill in skills[:5]:  # Show first 5
                context.append(f"  - {skill.name}")

        if state.scratchpad:
            context.append("\nPrevious actions:")
            for entry in state.scratchpad[-5:]:
                context.append(f"  {entry}")

        return "\n".join(context)

    def decide(self, state: SelfManagingState, observation: Dict[str, Any]) -> Decision[Action]:
        return None  # Engine uses LLM

    def reduce(
        self,
        state: SelfManagingState,
        observation: Dict[str, Any],
        decision: Decision[Action]
    ) -> SelfManagingState:
        # Record action (current_step is handled by Engine.advance_step())
        if decision.rationale:
            state.scratchpad.append(f"Thought: {decision.rationale[:100]}")

        if decision.actions:
            action = decision.actions[0]
            action_name = getattr(action, 'name', action.get('name', 'unknown'))
            state.scratchpad.append(f"Action: {action_name}")

        # Check if we installed skills during this step
        if observation and "action_results" in observation:
            for result in observation["action_results"]:
                result_str = str(result)
                # Detect successful skill installations
                if "Successfully installed skill" in result_str:
                    # Extract skill name from message
                    import re
                    match = re.search(r"skill '(\w+)'", result_str)
                    if match:
                        skill_name = match.group(1)
                        if skill_name not in state.installed_skills_during_run:
                            state.installed_skills_during_run.append(skill_name)
                            print(f"  [Agent] Skill '{skill_name}' added to active context")

        return state


def run_skill_workflow_demo():
    """Run the demo showing self-managing skill installation."""
    print("=" * 70)
    print("Self-Managing Skills Demo")
    print("=" * 70)
    print(f"\nModel: {MODEL_NAME}")
    print(f"SkillHub: {SKILLHUB_URL}")

    # Create LLM
    try:
        llm = OpenAIModel(
            model=MODEL_NAME,
            api_key=API_KEY,
            base_url=API_URL,
            temperature=0.7,
        )
        print("  ✓ LLM initialized")
    except Exception as e:
        print(f"  ✗ LLM init failed: {e}")
        return

    # Create agent
    agent = SelfManagingSkillAgent(llm=llm, skillhub_url=SKILLHUB_URL)

    # The key test: User asks the agent to manage skills itself
    user_task = f"""请先检查是否已安装 SkillHub 商店，若未安装，请根据
{SKILLHUB_URL}
安装Skillhub商店，但是只安装CLI，然后安装github技能。

若已安装，则直接安装github技能。

然后使用github技能列出GitHub仓库操作的要点。
"""

    print("\n" + "-" * 70)
    print("Running Task:")
    print(user_task)
    print("-" * 70)

    task = Task(
        id="skill_workflow",
        objective=user_task,
        budget=TaskBudget(max_steps=15),
    )

    try:
        # Add CLI rendering hook
        hooks = [ClaudeStyleHook(theme="default")]

        result = Engine(
            agent=agent,
            env=HostEnv(),
            history_policy=HistoryPolicy(max_messages=30),
            hooks=hooks,
        ).run(task)

        print("\n" + "=" * 70)
        print("Final Result")
        print("=" * 70)
        print(result.state.final_result or "(No final result)")

        print(f"\nSteps taken: {result.state.current_step}")
        print(f"Skills installed during run: {result.state.installed_skills_during_run}")

        print("\n" + "-" * 70)
        print("Trajecotry (what happened):")
        for entry in result.state.scratchpad:
            print(f"  {entry}")

    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()


def run_simple_test():
    """Simple test with English instructions."""
    print("=" * 70)
    print("Simple Self-Managing Skills Test")
    print("=" * 70)

    try:
        llm = OpenAIModel(
            model=MODEL_NAME,
            api_key=API_KEY,
            base_url=API_URL,
            temperature=0.7,
        )
    except Exception as e:
        print(f"LLM error: {e}")
        return

    agent = SelfManagingSkillAgent(llm=llm, skillhub_url=SKILLHUB_URL)

    # Clear English instructions
    task_text = """Please:
1. Check if the SkillHub is installed
2. If not installed, install it from https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/skillhub.md (CLI only)
3. Install the 'github' skill
4. List what the github skill tells you about working with repositories
"""

    print("\nTask:")
    print(task_text)

    task = Task(
        id="simple_skill_test",
        objective=task_text,
        budget=TaskBudget(max_steps=10),
    )

    env = HostEnv()

    # Add CLI rendering hook
    hooks = [ClaudeStyleHook(theme="default")]

    result = Engine(
        agent=agent,
        env=env,
        history_policy=HistoryPolicy(max_messages=20),
        hooks=hooks,
    ).run(task)

    print("\nResult:")
    print(result.state.final_result or "(No result)")


def main():
    print("QitOS Self-Managing Skills Demo")
    print("=" * 70)
    print("\nThis demonstrates agents that can:")
    print("1. Check if SkillHub is installed (check_skill_hub tool)")
    print("2. Install SkillHub if needed (install_skill_hub tool)")
    print("3. Install skills via hub (install_skill tool)")
    print("4. Use those skills to complete tasks")
    print()

    # Try the simple English version first
    run_simple_test()

    print("\n\n")

    # Then try the Chinese version
    run_skill_workflow_demo()


if __name__ == "__main__":
    main()
