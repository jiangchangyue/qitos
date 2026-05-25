# Contributing To QitOS

## Code Of Conduct

Participation in this project is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Ways To Contribute

- Improve docs, examples, and walkthroughs
- Add or refine tools, env integrations, and benchmark adapters
- Fix bugs or tighten framework contracts
- Improve tests, release hardening, and observability

## Development Setup

Use the quickstart install if you only want to run examples:

```bash
pip install -r requirements.txt
```

Use the full contributor setup for code changes:

```bash
git clone https://github.com/Qitor/qitos.git
cd qitos
pip install -r requirements-dev.txt
pre-commit install
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for common commands, coverage, troubleshooting, and docs workflow.

## Branch Naming

Use short branch names that reflect the change:

- `feat/<topic>`
- `fix/<topic>`
- `docs/<topic>`
- `refactor/<topic>`
- `chore/<topic>`

When using Codex or other assistants, `codex/<topic>` is also acceptable.

## Commit Messages

Prefer small, reviewable commits with imperative summaries:

- `feat: add model response summary to qita`
- `fix: preserve parser fallback after model interpretation`
- `docs: clarify coding toolset usage`

## Pull Request Process

Before opening a PR:

- Keep changes aligned with the `AgentModule + Engine` mental model
- Preserve or improve examples and docs when behavior changes
- Add or update tests for user-facing behavior
- Update [CHANGELOG.md](CHANGELOG.md) for high-signal user-facing changes
- Avoid unrelated cleanup in the same PR unless it directly unblocks the change

Boundary checklist:

- Is this generic framework code or product-specific app code?
- Does this belong in `qitos-zoo` instead?
- Does this add heavy dependencies to core?
- Does this expand the public API surface?
- Does this introduce security-sensitive behavior?
- Are tests and docs updated?

Before requesting review, run:

```bash
python -m pytest -q
python -m flake8 qitos/core qitos/engine qitos/models qitos/trace
python -m mypy qitos/core qitos/engine qitos/models qitos/trace
pytest --cov=qitos.core --cov=qitos.engine --cov=qitos.trace --cov-report=term --cov-fail-under=80 -q
python -m build
pip-audit
```

## Review Criteria

PRs are reviewed for:

- correctness and regression risk
- clarity of public surface changes
- documentation and migration quality
- test coverage for new behavior
- consistency with existing architecture boundaries

## Good First Areas

- walkthrough clarifications
- example polish
- benchmark docs
- toolset ergonomics
- qita UX improvements

---

## Contribution Templates

### Tool Contribution

Add a new tool to the QitOS tool registry.

**Directory structure:**
```
qitos/kit/tool/<tool_name>.py
tests/kit/tool/test_<tool_name>.py
```

**Code skeleton (`qitos/kit/tool/<tool_name>.py`):**
```python
"""<One-line description of the tool>."""
from __future__ import annotations
from typing import Any, Dict, List
from ...core.tool_schema import ToolSpec

def <tool_name>(<param>: <type>, **kwargs: Any) -> Dict[str, Any]:
    """<Tool description for LLM consumption>.

    Parameters
    ----------
    <param> : <type>
        <Description>

    Returns
    -------
    dict
        <Description of return value>
    """
    # Implementation
    return {"result": ...}

TOOL_SPEC = ToolSpec(
    name="<tool_name>",
    description="<Tool description>",
    parameters={
        "type": "object",
        "properties": {
            "<param>": {"type": "<type>", "description": "<desc>"},
        },
        "required": ["<param>"],
    },
)

# Set needs_approval=True if the tool has side effects
# needs_approval = True
```

**Test expectations (`tests/kit/tool/test_<tool_name>.py`):**
```python
"""Tests for <tool_name> tool."""
import pytest
from qitos.kit.tool.<tool_name> import <tool_name>, TOOL_SPEC

class Test<ToolName>:
    def test_spec_valid(self):
        assert TOOL_SPEC.name == "<tool_name>"
        assert "properties" in TOOL_SPEC.parameters

    def test_basic_invocation(self):
        result = <tool_name>(<param>=<value>)
        assert "result" in result

    def test_registry_integration(self):
        from qitos.core.tool_registry import ToolRegistry
        reg = ToolRegistry()
        reg.register(TOOL_SPEC, <tool_name>)
        assert reg.get("<tool_name>") is not None
```

**PR checklist:**
- [ ] Tool function has docstring consumable by LLMs
- [ ] `ToolSpec` matches function signature exactly
- [ ] `needs_approval` set if tool has side effects (shell, file write, etc.)
- [ ] Tool registered in appropriate `ToolSet` or exported from `__init__.py`
- [ ] Tests cover: basic invocation, edge cases, spec validity
- [ ] No heavy dependencies in core

---

### Parser Contribution

Add a new output parser for a model protocol variant.

**Directory structure:**
```
qitos/kit/parser/<parser_name>.py
tests/kit/parser/test_<parser_name>.py
```

**Code skeleton (`qitos/kit/parser/<parser_name>.py`):**
```python
"""<One-line description of the parser>."""
from __future__ import annotations
from typing import Any, List, Optional
from ...core.decision import Action, Decision

CONTRACT_ID = "<parser_name>_v1"

def parse(output: str, *, tool_registry: Any = None) -> Decision:
    """Parse model output into a Decision.

    Parameters
    ----------
    output : str
        Raw model output text.
    tool_registry : Any
        Tool registry for validation.

    Returns
    -------
    Decision
        Parsed decision with actions.
    """
    # Parse output and extract tool calls
    actions: List[Action] = []
    thought = output  # or extract reasoning
    return Decision(thought=thought, actions=actions)

def repair_renderer(parse_error: str, original_output: str) -> str:
    """Render a repair prompt for the model to fix its output.

    Parameters
    ----------
    parse_error : str
        Error message from the failed parse.
    original_output : str
        The original model output that failed to parse.

    Returns
    -------
    str
        Prompt fragment instructing the model to fix its output.
    """
    return f"Your previous output could not be parsed: {parse_error}. Please fix."
```

**Test expectations (`tests/kit/parser/test_<parser_name>.py`):**
```python
"""Tests for <parser_name> parser."""
import pytest
from qitos.kit.parser.<parser_name> import parse, repair_renderer, CONTRACT_ID

class Test<ParserName>:
    def test_contract_id_unique(self):
        from qitos.protocols import list_protocols
        # CONTRACT_ID should not collide with existing protocols
        existing = {p for p in list_protocols()}
        assert CONTRACT_ID not in existing or CONTRACT_ID == "<expected>"

    def test_parse_valid_output(self):
        decision = parse("<sample valid output>")
        assert decision is not None

    def test_parse_invalid_output(self):
        # Should raise or return empty actions
        decision = parse("gibberish")
        assert decision.actions == [] or decision is not None

    def test_repair_renderer(self):
        result = repair_renderer("missing JSON", "some output")
        assert len(result) > 0
```

**PR checklist:**
- [ ] `CONTRACT_ID` is unique across all parsers
- [ ] `parse()` returns a `Decision` with `thought` and `actions`
- [ ] `repair_renderer()` produces actionable fix instructions
- [ ] Parser registered in protocols table if it has a corresponding `ModelProtocol`
- [ ] Tests cover: valid output, invalid output, edge cases, contract uniqueness

---

### Protocol Contribution

Add a new `ModelProtocol` for a model family interaction style.

**Directory structure:**
```
qitos/protocols.py  (add entry to PROTOCOL_TABLE)
tests/test_model_protocols.py  (extend existing)
```

**Code skeleton (add to `qitos/protocols.py`):**
```python
<PROTOCOL_NAME> = ModelProtocol(
    id="<protocol_id>",
    display_name="<Display Name>",
    parser_factory="<parser_contract_id>",
    prompt_renderer=<render_function>,
    contract_renderer=<contract_string>,
    tool_schema_renderer=<schema_render_function>,
    tool_schema_delivery="prompt_injection",
    contract_version="v1",
    supports_multi_action=False,
    supports_native_tool_call_markup=False,
)
```

**Test expectations:**
```python
class Test<ProtocolName>:
    def test_protocol_registered(self):
        from qitos.protocols import get_protocol
        p = get_protocol("<protocol_id>")
        assert p is not None

    def test_protocol_fields(self):
        from qitos.protocols import get_protocol
        p = get_protocol("<protocol_id>")
        assert p.prompt_renderer is not None
        assert p.tool_schema_renderer is not None
        assert p.contract_renderer is not None

    def test_protocol_renders_valid_output(self):
        from qitos.protocols import render_protocol_prompt, get_protocol
        from qitos.core.tool_schema import ToolSpec
        p = get_protocol("<protocol_id>")
        prompt = render_protocol_prompt(p, task="test")
        assert len(prompt) > 0

    def test_fallback_chain_valid(self):
        from qitos.protocols import resolve_protocol_chain, get_protocol
        p = get_protocol("<protocol_id>")
        chain = resolve_protocol_chain(p)
        for proto_id in chain:
            assert get_protocol(proto_id) is not None
```

**PR checklist:**
- [ ] Protocol ID is unique
- [ ] All renderer functions produce non-empty output
- [ ] Fallback chain references only existing protocols
- [ ] `parser_factory` matches a registered parser's `CONTRACT_ID`
- [ ] FamilyPreset updated if this is a new model family
- [ ] Test matrix covers: prompt rendering, tool schema rendering, contract rendering, fallback chain

---

### Critic Contribution

Add a new critic using the `@critic` decorator.

**Directory structure:**
```
qitos/kit/critic/<critic_name>.py  (or qitos/engine/critic_decorator.py for built-ins)
tests/engine/test_critic_<name>.py
```

**Code skeleton (`qitos/kit/critic/<critic_name>.py`):**
```python
"""<One-line description of the critic>."""
from __future__ import annotations
from typing import Any
from ...engine.critic_decorator import critic
from ...engine.critic_result import CriticResult

@critic(name="<critic_name>", score=1.0)
def <critic_name>(state: Any, decision: Any, results: list) -> CriticResult | str | tuple:
    """<Description of what the critic evaluates>.

    Parameters
    ----------
    state : Any
        Current agent state.
    decision : Any
        The engine's decision for this step.
    results : list
        Results from tool execution.

    Returns
    -------
    CriticResult | str | tuple
        Quick-return shorthand:
        - ``"continue"`` — proceed normally
        - ``("stop", "reason")`` — stop execution
        - ``("retry", "reason", "instruction_patch")`` — retry with guidance
        - ``CriticResult(...)`` — full control
    """
    # Check some condition on state/decision/results
    if <condition>:
        return ("retry", "<reason>", "<instruction_patch>")

    return "continue"
```

**Test expectations (`tests/engine/test_critic_<name>.py`):**
```python
"""Tests for <critic_name> critic."""
import pytest
from qitos.engine.critic import Critic
from qitos.kit.critic.<critic_name> import <critic_name>

class Test<CriticName>:
    def test_is_critic_instance(self):
        assert isinstance(<critic_name>, Critic)

    def test_name(self):
        assert <critic_name>.name == "<critic_name>"

    def test_continue_on_normal(self):
        # Set up normal state/decision/results
        result = <critic_name>.evaluate(state, decision, results)
        assert result.action == "continue"

    def test_retry_on_condition(self):
        # Set up state that triggers retry
        result = <critic_name>.evaluate(state, decision, results)
        assert result.action == "retry"
        assert result.instruction_patch is not None

    def test_stop_on_exhaustion(self):
        # Set up state that triggers stop
        result = <critic_name>.evaluate(state, decision, results)
        assert result.action == "stop"

    def test_compatible_with_engine(self):
        from qitos.engine.engine import Engine
        # Can be added via engine.add_critic()
        # engine.add_critic(<critic_name>) should work
```

**PR checklist:**
- [ ] Critic uses `@critic` decorator (not raw `Critic` subclass)
- [ ] Returns quick-return shorthand or `CriticResult`
- [ ] `name` and `score` parameters set appropriately
- [ ] Compatible with `engine.add_critic()`
- [ ] Tests cover: continue, retry, stop, engine integration
- [ ] No side effects in critic evaluation
