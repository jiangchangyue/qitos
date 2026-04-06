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

## For Contributors

Clone the repository and install in editable mode:

```bash
git clone https://github.com/Qitor/qitos.git
cd qitos
pip install -e ".[dev,models,benchmarks]"
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
- [docs/requirements.txt](https://github.com/Qitor/qitos/blob/main/docs/requirements.txt)
