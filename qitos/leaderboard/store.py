"""SQLite-backed leaderboard store for benchmark result submission and ranking."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import LeaderboardSubmission

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS submissions (
    submission_id  TEXT PRIMARY KEY,
    benchmark      TEXT NOT NULL,
    split          TEXT NOT NULL,
    task_id        TEXT NOT NULL,
    model_name     TEXT NOT NULL DEFAULT '',
    model_family   TEXT NOT NULL DEFAULT '',
    prompt_protocol TEXT NOT NULL DEFAULT '',
    parser_name    TEXT NOT NULL DEFAULT '',
    success        INTEGER NOT NULL DEFAULT 0,
    stop_reason    TEXT NOT NULL DEFAULT '',
    steps          INTEGER NOT NULL DEFAULT 0,
    latency_seconds REAL NOT NULL DEFAULT 0.0,
    token_usage    INTEGER NOT NULL DEFAULT 0,
    cost           REAL NOT NULL DEFAULT 0.0,
    is_official    INTEGER NOT NULL DEFAULT 0,
    run_spec_json  TEXT NOT NULL DEFAULT '{}',
    result_json    TEXT NOT NULL DEFAULT '{}',
    trace_artifacts_dir TEXT NOT NULL DEFAULT '',
    git_sha        TEXT NOT NULL DEFAULT '',
    package_version TEXT NOT NULL DEFAULT '',
    submitted_at   TEXT NOT NULL,
    fingerprint    TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_dedup
    ON submissions(benchmark, split, task_id, fingerprint);

CREATE INDEX IF NOT EXISTS idx_sub_benchmark
    ON submissions(benchmark, split);

CREATE INDEX IF NOT EXISTS idx_sub_model
    ON submissions(model_name);

CREATE INDEX IF NOT EXISTS idx_sub_official
    ON submissions(is_official, benchmark, split);
"""


class LeaderboardStore:
    """SQLite-backed leaderboard store.

    Args:
        db_path: Path to the SQLite database file.
            Use ``":memory:"`` for an in-memory database (testing only).
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def __enter__(self) -> LeaderboardStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ---- public API ----

    def submit(
        self,
        run_spec: Any,
        result: Any,
        trace_artifacts_dir: Optional[str] = None,
    ) -> str:
        """Insert one benchmark result. Returns submission_id.

        Deduplicates by (benchmark, split, task_id, fingerprint) using INSERT OR IGNORE.
        """
        from qitos.core.spec import RunSpec, BenchmarkRunResult

        rs = RunSpec.from_value(run_spec)
        br = BenchmarkRunResult.from_value(result)

        is_official = rs.is_official_run()
        fingerprint = rs.fingerprint()
        submission_id = uuid4().hex[:16]
        submitted_at = datetime.now(timezone.utc).isoformat()

        with self._conn:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO submissions "
                "(submission_id, benchmark, split, task_id, model_name, model_family, "
                "prompt_protocol, parser_name, success, stop_reason, steps, "
                "latency_seconds, token_usage, cost, is_official, run_spec_json, "
                "result_json, trace_artifacts_dir, git_sha, package_version, "
                "submitted_at, fingerprint) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    submission_id,
                    br.benchmark,
                    br.split,
                    br.task_id,
                    rs.model_name or "",
                    rs.model_family or "",
                    rs.prompt_protocol or "",
                    rs.parser_name or "",
                    int(br.success),
                    br.stop_reason or "",
                    int(br.steps or 0),
                    float(br.latency_seconds or 0),
                    int(br.token_usage or 0),
                    float(br.cost or 0),
                    int(is_official),
                    json.dumps(rs.to_dict(), ensure_ascii=False),
                    json.dumps(br.to_dict(), ensure_ascii=False),
                    trace_artifacts_dir or "",
                    rs.git_sha or "",
                    rs.package_version or "",
                    submitted_at,
                    fingerprint,
                ),
            )
            if cursor.rowcount == 0:
                # Deduplicated — return existing submission_id
                cur2 = self._conn.execute(
                    "SELECT submission_id FROM submissions "
                    "WHERE benchmark = ? AND split = ? AND task_id = ? AND fingerprint = ?",
                    (br.benchmark, br.split, br.task_id, fingerprint),
                )
                row = cur2.fetchone()
                return row[0] if row else submission_id

        return submission_id

    def submit_results_file(self, path: str | Path) -> int:
        """Read a JSONL results file and submit all rows.

        Returns the number of new submissions inserted.
        """
        from qitos.benchmark.common import read_benchmark_results

        rows = read_benchmark_results(path)
        count = 0
        for row in rows:
            run_spec_dict = {}
            if row.run_spec_ref:
                try:
                    run_spec_dict = json.loads(row.run_spec_ref)
                except (json.JSONDecodeError, TypeError):
                    pass
            sid = self.submit(run_spec=run_spec_dict, result=row, trace_artifacts_dir=row.trace_run_dir)
            if sid:
                count += 1
        return count

    def submit_run_dir(self, run_dir: str | Path) -> str:
        """Load a run directory's manifest.json and submit as a result.

        Returns submission_id.
        """
        run_path = Path(run_dir).expanduser().resolve()
        manifest_path = run_path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest.json in {run_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        run_spec_dict = manifest.get("run_spec", {})
        summary = manifest.get("summary", {})

        from qitos.core.spec import BenchmarkRunResult

        result = BenchmarkRunResult(
            task_id=manifest.get("run_id", run_path.name),
            benchmark=manifest.get("benchmark_name", ""),
            split=manifest.get("benchmark_split", ""),
            prediction=summary.get("final_result"),
            success=summary.get("stop_reason") == "completed",
            stop_reason=summary.get("stop_reason", ""),
            steps=int(manifest.get("step_count", 0)),
            latency_seconds=float(manifest.get("latency_seconds", 0)),
            token_usage=int(manifest.get("token_usage", {}).get("total", 0)),
            cost=float(manifest.get("cost", 0)),
            trace_run_dir=str(run_path),
            run_spec_ref=json.dumps(run_spec_dict, ensure_ascii=False),
        )

        return self.submit(run_spec=run_spec_dict, result=result, trace_artifacts_dir=str(run_path))

    def query(
        self,
        *,
        benchmark: Optional[str] = None,
        split: Optional[str] = None,
        model_name: Optional[str] = None,
        is_official: Optional[bool] = None,
        sort_by: str = "submitted_at",
        limit: int = 50,
    ) -> List[LeaderboardSubmission]:
        """Query submissions with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []

        if benchmark is not None:
            clauses.append("benchmark = ?")
            params.append(benchmark)
        if split is not None:
            clauses.append("split = ?")
            params.append(split)
        if model_name is not None:
            clauses.append("model_name = ?")
            params.append(model_name)
        if is_official is not None:
            clauses.append("is_official = ?")
            params.append(int(is_official))

        where = " AND ".join(clauses) if clauses else "1=1"
        allowed_sort = {
            "submitted_at", "benchmark", "model_name", "steps",
            "latency_seconds", "cost", "success",
        }
        order_col = sort_by if sort_by in allowed_sort else "submitted_at"
        sql = f"SELECT * FROM submissions WHERE {where} ORDER BY {order_col} DESC LIMIT ?"
        params.append(limit)

        cur = self._conn.execute(sql, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        results: List[LeaderboardSubmission] = []
        for row in rows:
            d = dict(zip(columns, row))
            d["success"] = bool(d.get("success", 0))
            d["is_official"] = bool(d.get("is_official", 0))
            results.append(LeaderboardSubmission.from_value(d))
        return results

    def summary(
        self,
        benchmark: str,
        split: str,
        is_official: bool = True,
    ) -> Dict[str, Any]:
        """Compute aggregated statistics for a benchmark/split."""
        cur = self._conn.execute(
            "SELECT success, steps, latency_seconds, token_usage, cost "
            "FROM submissions WHERE benchmark = ? AND split = ? AND is_official = ?",
            (benchmark, split, int(is_official)),
        )
        rows = cur.fetchall()
        total = len(rows)
        if total == 0:
            return {
                "benchmark": benchmark,
                "split": split,
                "total": 0,
                "success_rate": 0.0,
                "avg_steps": 0.0,
                "avg_latency": 0.0,
                "total_cost": 0.0,
            }

        success_count = sum(1 for r in rows if r[0])
        return {
            "benchmark": benchmark,
            "split": split,
            "total": total,
            "success_rate": round(success_count / total, 4),
            "avg_steps": round(sum(r[1] for r in rows) / total, 2),
            "avg_latency": round(sum(r[2] for r in rows) / total, 2),
            "total_cost": round(sum(r[4] for r in rows), 4),
        }


__all__ = ["LeaderboardStore"]
