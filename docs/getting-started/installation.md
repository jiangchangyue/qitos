# Installation

## Requirements

- Python 3.9+

## For Users

Install the package from PyPI:

```bash
pip install qitos
```

Optional extras:

```bash
pip install "qitos[models,benchmarks]"
```

`qitos[models]` currently bundles optional SDK dependencies for:

- OpenAI-compatible providers via `openai`
- LiteLLM via `litellm`

Anthropic native Messages API, Google Gemini native API, Ollama, and LM Studio
adapters are available in `qitos.models` without extra provider SDKs.

## For Contributors

Clone the repository and install in editable mode:

```bash
git clone https://github.com/Qitor/qitos.git
cd qitos
pip install -r requirements.txt
```

For the full contributor toolchain:

```bash
pip install -r requirements-dev.txt
```

Run the supported test suite from the repo root:

```bash
python -m pytest -q
```

## For Docs Work

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

## Source Index

- [setup.py](https://github.com/Qitor/qitos/blob/main/setup.py)
- [requirements.txt](https://github.com/Qitor/qitos/blob/main/requirements.txt)
- [requirements-dev.txt](https://github.com/Qitor/qitos/blob/main/requirements-dev.txt)
- [docs/requirements.txt](https://github.com/Qitor/qitos/blob/main/docs/requirements.txt)
