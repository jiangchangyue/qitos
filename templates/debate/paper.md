# Debate Pattern

Two agents argue for and against a proposition, with a judge deciding the winner.

## Architecture

```
Proponent ──handoff──> Opponent ──handoff──> Judge
    ^                      |                    |
    └──────────────────────┘                    |
                                                v
                                          Verdict
```

## Configuration

Set the proposition and round count in `config.yaml`.

## Handoff Context

- **Proponent → Opponent**: Summary strategy (compressed history)
- **Opponent → Judge**: Full strategy (complete debate history)
- **SharedMemory**: `arguments`, `round`, `verdict` fields

## Usage

```python
from qitos.templates.debate.agent import DebateConfig, build_debate_system

config = DebateConfig(proposition="AI should be regulated", max_rounds=3)
system = build_debate_system(config)
```
