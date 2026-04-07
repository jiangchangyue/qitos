# 安装

## 环境要求

- Python 3.9+

## 普通用户安装

直接从 PyPI 安装：

```bash
pip install qitos
```

可选扩展：

```bash
pip install "qitos[models,benchmarks]"
```

`qitos[models]` 目前会安装这些可选模型依赖：

- 通过 `openai` 接 OpenAI-compatible provider
- 通过 `litellm` 接 LiteLLM

Anthropic 原生 Messages API、Google Gemini 原生 API、Ollama、LM Studio
适配器都直接在 `qitos.models` 中可用，不额外依赖 provider SDK。

## 贡献者安装

克隆仓库并以 editable 模式安装：

```bash
git clone https://github.com/Qitor/qitos.git
cd qitos
pip install -r requirements.txt
```

如果需要完整开发工具链：

```bash
pip install -r requirements-dev.txt
```

在仓库根目录运行支持的测试集：

```bash
python -m pytest -q
```

## 文档开发

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

## Source Index

- [setup.py](https://github.com/Qitor/qitos/blob/main/setup.py)
- [requirements.txt](https://github.com/Qitor/qitos/blob/main/requirements.txt)
- [requirements-dev.txt](https://github.com/Qitor/qitos/blob/main/requirements-dev.txt)
- [docs/requirements.txt](https://github.com/Qitor/qitos/blob/main/docs/requirements.txt)
