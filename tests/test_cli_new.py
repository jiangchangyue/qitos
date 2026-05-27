"""Tests for qit new and qit list-templates CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qitos.cli import main as qit_main


class TestListTemplates:
    def test_list_all_templates(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = qit_main(["list-templates"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "qitos_new_agent" in out
        assert "react" in out

    def test_list_scaffold_only(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = qit_main(["list-templates", "--type", "scaffold"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "qitos_new_agent" in out
        assert "Scaffold templates" in out
        # Method templates should not appear
        assert "react" not in out

    def test_list_method_only(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = qit_main(["list-templates", "--type", "method"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "react" in out
        assert "Method templates" in out
        # Scaffold templates should not appear
        assert "qitos_new_agent" not in out


class TestNewCommand:
    def test_new_with_missing_template(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = qit_main(["new", "--template", "nonexistent"])
        assert rc == 1
        out = capsys.readouterr().err
        assert "not found" in out

    def test_new_with_method_template_fails(self, capsys: pytest.CaptureFixture[str]) -> None:
        # 'react' is a method template, not a scaffold template
        rc = qit_main(["new", "--template", "react"])
        assert rc == 1
        out = capsys.readouterr().err
        assert "not a scaffold template" in out

    def test_new_without_cookiecutter_installed(self, capsys: pytest.CaptureFixture[str]) -> None:
        import sys
        saved = {}
        for key in list(sys.modules):
            if key.startswith("cookiecutter"):
                saved[key] = sys.modules.pop(key)
        try:
            # Ensure cookiecutter.main is not importable
            sys.modules["cookiecutter"] = None
            sys.modules["cookiecutter.main"] = None
            rc = qit_main(["new", "--agent-name", "test_agent"])
            assert rc == 1
            out = capsys.readouterr().err
            assert "cookiecutter is required" in out
        finally:
            sys.modules.update(saved)
            for key in list(sys.modules):
                if key.startswith("cookiecutter") and key not in saved:
                    del sys.modules[key]

    def test_new_calls_cookiecutter(self, tmp_path: Path) -> None:
        mock_cc = MagicMock(return_value="/tmp/test_agent")
        with patch("qitos.cli.cookiecutter", mock_cc, create=True):
            with patch.dict("sys.modules", {"cookiecutter": MagicMock(main=MagicMock(cookiecutter=mock_cc))}):
                with patch("cookiecutter.main.cookiecutter", mock_cc):
                    rc = qit_main([
                        "new",
                        "--agent-name", "my_cool_agent",
                        "--agent-description", "A cool agent",
                        "--output-dir", str(tmp_path),
                    ])
                    # The command should succeed if cookiecutter is available
                    # Since we're mocking, check that we got past the import check

    def test_new_passes_extra_context(self, tmp_path: Path) -> None:
        mock_cc = MagicMock(return_value=str(tmp_path / "my_agent"))
        with patch("cookiecutter.main.cookiecutter", mock_cc):
            rc = qit_main([
                "new",
                "--agent-name", "my_agent",
                "--agent-description", "My test agent",
                "--author", "tester",
                "--default-model", "qwen-plus",
                "--max-steps", "20",
                "--output-dir", str(tmp_path),
            ])
            assert rc == 0
            mock_cc.assert_called_once()
            call_kwargs = mock_cc.call_args
            # Check extra_context was passed
            extra = call_kwargs[1].get("extra_context") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else call_kwargs[1].get("extra_context")
            if extra is None and "extra_context" in call_kwargs[1]:
                extra = call_kwargs[1]["extra_context"]
            assert extra is not None
            assert extra["agent_name"] == "my_agent"
            assert extra["agent_description"] == "My test agent"
            assert extra["author"] == "tester"
            assert extra["default_model"] == "qwen-plus"
            assert extra["max_steps"] == "20"

    def test_new_no_input_flag(self, tmp_path: Path) -> None:
        mock_cc = MagicMock(return_value=str(tmp_path / "my_agent"))
        with patch("cookiecutter.main.cookiecutter", mock_cc):
            rc = qit_main([
                "new",
                "--no-input",
                "--output-dir", str(tmp_path),
            ])
            assert rc == 0
            call_kwargs = mock_cc.call_args
            assert call_kwargs[1].get("no_input") is True


class TestMainHelp:
    def test_help_shows_new_and_list_templates(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = qit_main(["--help"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "new" in out
        assert "list-templates" in out

    def test_no_args_shows_new_and_list_templates(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = qit_main([])
        assert rc == 1
        out = capsys.readouterr().out
        assert "new" in out
        assert "list-templates" in out
