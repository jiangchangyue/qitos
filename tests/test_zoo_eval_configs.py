"""Tests for zoo package eval_config.yaml files."""
from __future__ import annotations

import os
from pathlib import Path

import yaml


_ZOO_ROOT = Path(__file__).resolve().parent.parent / "qitos_zoo"


def _load_eval_config(package_name: str) -> dict:
    """Load eval_config.yaml from a zoo package."""
    path = _ZOO_ROOT / package_name / "eval_config.yaml"
    assert path.exists(), f"{package_name}/eval_config.yaml not found"
    with open(path) as f:
        return yaml.safe_load(f)


def test_cyber_eval_config_exists_and_valid():
    """qitos_cyber has a valid eval_config.yaml."""
    cfg = _load_eval_config("qitos_cyber")
    assert cfg["agent"]["name"] == "qitos_cyber"
    assert "benchmarks" in cfg
    assert "serialization" in cfg
    assert "defaults" in cfg


def test_swe_eval_config_exists_and_valid():
    """qitos_swe has a valid eval_config.yaml."""
    cfg = _load_eval_config("qitos_swe")
    assert cfg["agent"]["name"] == "qitos_swe"
    assert "benchmarks" in cfg


def test_coder_eval_config_exists_and_valid():
    """qitos_coder has a valid eval_config.yaml."""
    cfg = _load_eval_config("qitos_coder")
    assert cfg["agent"]["name"] == "qitos_coder"
    assert "factory" in cfg["agent"]
    assert "benchmarks" in cfg
    assert "required_tools" in cfg["agent"]
    assert "serialization" in cfg
    assert "defaults" in cfg


def test_auditor_eval_config_exists_and_valid():
    """qitos_auditor has a valid eval_config.yaml."""
    cfg = _load_eval_config("qitos_auditor")
    assert cfg["agent"]["name"] == "qitos_auditor"
    assert "factory" in cfg["agent"]
    assert "benchmarks" in cfg
    assert "required_tools" in cfg["agent"]


def test_coder_eval_config_factory_matches_snowl_compat():
    """qitos_coder eval_config factory references correct snowl_compat function."""
    cfg = _load_eval_config("qitos_coder")
    factory = cfg["agent"]["factory"]
    assert "qitos_coder.snowl_compat.create_snowl_agent" in factory


def test_auditor_eval_config_factory_matches_snowl_compat():
    """qitos_auditor eval_config factory references correct snowl_compat function."""
    cfg = _load_eval_config("qitos_auditor")
    factory = cfg["agent"]["factory"]
    assert "qitos_auditor.snowl_compat.create_snowl_agent" in factory


def test_all_zoo_packages_with_snowl_compat_have_eval_config():
    """Every zoo package with snowl_compat.py should have eval_config.yaml."""
    for pkg_dir in sorted(_ZOO_ROOT.iterdir()):
        if not pkg_dir.is_dir():
            continue
        if pkg_dir.name.startswith("_"):
            continue
        snowl_compat = pkg_dir / "snowl_compat.py"
        if snowl_compat.exists():
            eval_cfg = pkg_dir / "eval_config.yaml"
            assert eval_cfg.exists(), (
                f"{pkg_dir.name} has snowl_compat.py but no eval_config.yaml"
            )
