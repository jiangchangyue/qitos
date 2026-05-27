"""Tests for qitos.hf — HF Hub push/pull and manifest sanitization."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from qitos.hf.hub import sanitize_manifest


class TestSanitizeManifest:
    def test_removes_api_key(self):
        manifest = {
            "run_spec": {
                "environment": {
                    "api_key": "sk-secret123",
                    "base_url": "https://api.example.com/v1/",
                    "other": "keep",
                }
            }
        }
        result = sanitize_manifest(manifest)
        assert "api_key" not in result["run_spec"]["environment"]
        assert result["run_spec"]["environment"]["base_url"] == "REDACTED"
        assert result["run_spec"]["environment"]["other"] == "keep"

    def test_removes_sensitive_keys(self):
        manifest = {
            "run_spec": {
                "environment": {
                    "SECRET_TOKEN": "abc",
                    "password": "pass123",
                    "api_key_value": "sk-...",
                    "safe_key": "keep",
                }
            }
        }
        result = sanitize_manifest(manifest)
        assert "SECRET_TOKEN" not in result["run_spec"]["environment"]
        assert "password" not in result["run_spec"]["environment"]
        assert "api_key_value" not in result["run_spec"]["environment"]
        assert result["run_spec"]["environment"]["safe_key"] == "keep"

    def test_does_not_mutate_original(self):
        manifest = {
            "run_spec": {
                "environment": {
                    "api_key": "sk-secret",
                    "base_url": "https://api.example.com",
                }
            }
        }
        import copy
        original = copy.deepcopy(manifest)
        sanitize_manifest(manifest)
        assert manifest == original

    def test_no_run_spec(self):
        manifest = {"schema_version": "v1", "step_count": 5}
        result = sanitize_manifest(manifest)
        assert result == manifest

    def test_no_environment(self):
        manifest = {"run_spec": {"model_name": "qwen"}}
        result = sanitize_manifest(manifest)
        assert result["run_spec"]["model_name"] == "qwen"

    def test_empty_environment(self):
        manifest = {"run_spec": {"environment": {}}}
        result = sanitize_manifest(manifest)
        assert result["run_spec"]["environment"] == {}


class TestPushRun:
    @patch("qitos.hf.hub._require_hf")
    def test_push_run_calls_upload(self, mock_require):
        import tempfile
        from pathlib import Path

        mock_hf = MagicMock()
        mock_require.return_value = mock_hf

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run_001"
            run_dir.mkdir()
            (run_dir / "manifest.json").write_text(json.dumps({
                "run_spec": {"environment": {"api_key": "sk-secret"}},
            }))
            (run_dir / "events.jsonl").write_text('{"step_id":0}\n')
            (run_dir / "steps.jsonl").write_text('{"step_id":0}\n')

            from qitos.hf.hub import push_run
            url = push_run(str(run_dir), "user/qitos-traces", private=True)

            assert "user/qitos-traces" in url
            mock_hf.create_repo.assert_called_once()
            assert mock_hf.upload_file.call_count >= 3

    @patch("qitos.hf.hub._require_hf")
    def test_push_nonexistent_dir(self, mock_require):
        from qitos.hf.hub import push_run
        with pytest.raises(FileNotFoundError):
            push_run("/nonexistent/dir", "user/repo")


class TestPullRun:
    @patch("qitos.hf.hub._require_hf")
    def test_pull_run_calls_download(self, mock_require):
        import tempfile
        from pathlib import Path

        mock_hf = MagicMock()
        mock_require.return_value = mock_hf

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock download structure
            cached_dir = Path(tmpdir) / "cache" / "run_001"
            cached_dir.mkdir(parents=True)
            (cached_dir / "manifest.json").write_text("{}")
            mock_hf.snapshot_download.return_value = str(Path(tmpdir) / "cache")

            from qitos.hf.hub import pull_run
            result = pull_run("run_001", "user/repo", tmpdir)
            mock_hf.snapshot_download.assert_called_once()
            assert result.name == "run_001"


class TestListRemoteRuns:
    @patch("qitos.hf.hub._require_hf")
    def test_list_remote_runs(self, mock_require):
        mock_hf = MagicMock()
        mock_require.return_value = mock_hf

        item1 = MagicMock()
        item1.path = "run_001"
        item2 = MagicMock()
        item2.path = "run_002"
        mock_hf.list_repo_tree.return_value = [item1, item2]

        from qitos.hf.hub import list_remote_runs
        runs = list_remote_runs("user/repo")
        assert "run_001" in runs
        assert "run_002" in runs

    @patch("qitos.hf.hub._require_hf")
    def test_list_remote_runs_error(self, mock_require):
        mock_hf = MagicMock()
        mock_require.return_value = mock_hf
        mock_hf.list_repo_tree.side_effect = Exception("not found")

        from qitos.hf.hub import list_remote_runs
        runs = list_remote_runs("user/repo")
        assert runs == []
