"""Tests for qitos.leaderboard — SQLite-backed benchmark ranking."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from qitos.core.spec import BenchmarkRunResult, RunSpec
from qitos.leaderboard.models import LeaderboardSubmission
from qitos.leaderboard.store import LeaderboardStore


# ---- helpers ----

def _make_run_spec(**overrides):
    defaults = {
        "model_name": "Qwen/Qwen3-8B",
        "prompt_protocol": "react_text_v1",
        "parser_name": "ReActTextParser",
        "trace_schema_version": "v1",
        "benchmark_name": "gaia",
        "benchmark_split": "test",
    }
    defaults.update(overrides)
    return RunSpec(**defaults)


def _make_result(**overrides):
    defaults = {
        "task_id": "task_001",
        "benchmark": "gaia",
        "split": "test",
        "prediction": "A",
        "success": True,
        "stop_reason": "completed",
        "steps": 5,
        "latency_seconds": 12.3,
        "token_usage": 1500,
        "cost": 0.02,
        "trace_run_dir": "/tmp/run1",
        "run_spec_ref": None,
    }
    defaults.update(overrides)
    return BenchmarkRunResult(**defaults)


# ---- LeaderboardSubmission ----

class TestLeaderboardSubmission:
    def test_to_dict_roundtrip(self):
        s = LeaderboardSubmission(
            submission_id="abc", benchmark="gaia", split="test",
            task_id="t1", model_name="qwen", fingerprint="fp1",
            submitted_at="2026-01-01", is_official=True,
        )
        d = s.to_dict()
        assert d["submission_id"] == "abc"
        assert d["is_official"] is True
        s2 = LeaderboardSubmission.from_value(d)
        assert s2.submission_id == "abc"

    def test_from_value_ignores_unknown_keys(self):
        s = LeaderboardSubmission.from_value({"submission_id": "x", "unknown": 42})
        assert s.submission_id == "x"
        assert s.benchmark == ""
        assert s.split == ""
        assert s.task_id == ""


# ---- LeaderboardStore ----

class TestLeaderboardStore:
    def test_submit_and_query(self):
        with LeaderboardStore(":memory:") as store:
            rs = _make_run_spec()
            br = _make_result()
            sid = store.submit(rs, br)
            assert sid

            rows = store.query(benchmark="gaia")
            assert len(rows) == 1
            assert rows[0].submission_id == sid
            assert rows[0].model_name == "Qwen/Qwen3-8B"
            assert rows[0].is_official is True

    def test_submit_is_official_false_when_missing_fields(self):
        with LeaderboardStore(":memory:") as store:
            rs = RunSpec(model_name="", prompt_protocol="")
            br = _make_result()
            store.submit(rs, br)
            rows = store.query()
            assert rows[0].is_official is False

    def test_deduplication_on_fingerprint(self):
        with LeaderboardStore(":memory:") as store:
            rs = _make_run_spec()
            br = _make_result()
            sid1 = store.submit(rs, br)
            sid2 = store.submit(rs, br)
            assert sid1 == sid2  # INSERT OR IGNORE
            rows = store.query()
            assert len(rows) == 1

    def test_different_tasks_not_deduped(self):
        with LeaderboardStore(":memory:") as store:
            rs = _make_run_spec()
            br1 = _make_result(task_id="t1")
            br2 = _make_result(task_id="t2")
            store.submit(rs, br1)
            store.submit(rs, br2)
            rows = store.query()
            assert len(rows) == 2

    def test_query_filters(self):
        with LeaderboardStore(":memory:") as store:
            rs_gaia = _make_run_spec(benchmark_name="gaia")
            rs_tau = _make_run_spec(benchmark_name="tau-bench")
            store.submit(rs_gaia, _make_result(benchmark="gaia"))
            store.submit(rs_tau, _make_result(benchmark="tau-bench", task_id="t2"))
            assert len(store.query(benchmark="gaia")) == 1
            assert len(store.query(benchmark="tau-bench")) == 1
            assert len(store.query()) == 2

    def test_query_model_filter(self):
        with LeaderboardStore(":memory:") as store:
            store.submit(_make_run_spec(), _make_result())
            store.submit(
                _make_run_spec(model_name="gpt-4"),
                _make_result(task_id="t2"),
            )
            assert len(store.query(model_name="Qwen/Qwen3-8B")) == 1
            assert len(store.query(model_name="gpt-4")) == 1

    def test_query_official_filter(self):
        with LeaderboardStore(":memory:") as store:
            store.submit(_make_run_spec(), _make_result())
            store.submit(
                RunSpec(model_name=""),
                _make_result(task_id="t2"),
            )
            assert len(store.query(is_official=True)) == 1
            assert len(store.query(is_official=False)) == 1

    def test_query_limit(self):
        with LeaderboardStore(":memory:") as store:
            for i in range(10):
                store.submit(
                    _make_run_spec(),
                    _make_result(task_id=f"t{i}"),
                )
            assert len(store.query(limit=3)) == 3

    def test_summary(self):
        with LeaderboardStore(":memory:") as store:
            store.submit(_make_run_spec(), _make_result(success=True))
            store.submit(
                _make_run_spec(),
                _make_result(task_id="t2", success=False),
            )
            s = store.summary("gaia", "test", is_official=True)
            assert s["total"] == 2
            assert s["success_rate"] == 0.5

    def test_summary_empty(self):
        with LeaderboardStore(":memory:") as store:
            s = store.summary("gaia", "test")
            assert s["total"] == 0

    def test_submit_results_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "results.jsonl"
            rs = _make_run_spec()
            br = _make_result()
            with path.open("w") as f:
                f.write(json.dumps(br.to_dict(), ensure_ascii=False) + "\n")
                br2 = _make_result(task_id="t2")
                f.write(json.dumps(br2.to_dict(), ensure_ascii=False) + "\n")

            with LeaderboardStore(":memory:") as store:
                count = store.submit_results_file(str(path))
                assert count == 2

    def test_submit_run_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run_001"
            run_dir.mkdir()
            manifest = {
                "run_id": "run_001",
                "benchmark_name": "gaia",
                "benchmark_split": "test",
                "step_count": 5,
                "summary": {"stop_reason": "completed", "final_result": "A"},
                "latency_seconds": 10.5,
                "token_usage": {"total": 1200},
                "cost": 0.015,
                "run_spec": _make_run_spec().to_dict(),
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))

            with LeaderboardStore(":memory:") as store:
                sid = store.submit_run_dir(str(run_dir))
                assert sid
                rows = store.query()
                assert len(rows) == 1
                assert rows[0].success is True

    def test_submit_run_dir_missing_manifest(self):
        with LeaderboardStore(":memory:") as store:
            with pytest.raises(FileNotFoundError):
                store.submit_run_dir("/nonexistent/path")

    def test_context_manager(self):
        store = LeaderboardStore(":memory:")
        with store:
            store.submit(_make_run_spec(), _make_result())
            assert len(store.query()) == 1
