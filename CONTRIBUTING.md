# Contributing To QitOS

## Ways To Contribute

- Improve docs, examples, and walkthroughs
- Add or refine tools, env integrations, and benchmark adapters
- Fix bugs or tighten framework contracts
- Improve tests, release hardening, and observability

## Development Setup

```bash
git clone https://github.com/Qitor/qitos.git
cd qitos
pip install -e ".[dev,models,benchmarks]"
```

Run the supported test suite:

```bash
python -m pytest -q
```

## Docs Workflow

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

## Pull Request Checklist

- Keep changes aligned with the `AgentModule + Engine` mental model
- Preserve or improve examples and docs when behavior changes
- Add or update tests for user-facing behavior
- Keep Python version expectations consistent across README, docs, and package metadata
- Avoid unrelated cleanup in the same PR unless it directly unblocks the change

## Good First Areas

- walkthrough clarifications
- example polish
- benchmark docs
- toolset ergonomics
- qita UX improvements
