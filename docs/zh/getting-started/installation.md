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

## 贡献者安装

克隆仓库并以 editable 模式安装：

```bash
git clone https://github.com/Qitor/qitos.git
cd qitos
pip install -e ".[dev,models,benchmarks]"
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
- [docs/requirements.txt](https://github.com/Qitor/qitos/blob/main/docs/requirements.txt)
