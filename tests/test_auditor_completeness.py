"""Tests for auditor completeness — A-6 through A-10 tools, AuditFinding, AuditReport."""
from __future__ import annotations

import tempfile

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_toolset():
    from qitos_zoo.qitos_auditor.tools.audit_toolset import AuditToolSet

    with tempfile.TemporaryDirectory() as tmp:
        return AuditToolSet(workspace_root=tmp)


# ---------------------------------------------------------------------------
# A-6 audit_generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:

    def test_json_format(self):
        ts = _make_toolset()
        findings = [
            {"id": "F1", "severity": "high", "title": "SQLi", "description": "SQL injection"},
            {"id": "F2", "severity": "low", "title": "Typo", "description": "Typo in comment"},
        ]
        result = ts.generate_report(findings=findings, format="json", output_path="/tmp/report.json")
        assert result["status"] == "ok"
        assert result["format"] == "json"
        assert result["output_path"] == "/tmp/report.json"
        assert result["report_summary"]["total_findings"] == 2
        assert result["report_summary"]["by_severity"]["high"] == 1
        assert result["report_summary"]["by_severity"]["low"] == 1

    def test_sarif_format(self):
        ts = _make_toolset()
        findings = [{"id": "F1", "severity": "critical", "description": "RCE"}]
        result = ts.generate_report(findings=findings, format="sarif", output_path="/tmp/report.sarif")
        assert result["status"] == "ok"
        assert result["format"] == "sarif"

    def test_markdown_format(self):
        ts = _make_toolset()
        findings = [{"id": "F1", "severity": "medium", "title": "Weak hash", "description": "MD5 used"}]
        result = ts.generate_report(findings=findings, format="markdown", output_path="/tmp/report.md")
        assert result["status"] == "ok"
        assert result["format"] == "markdown"

    def test_invalid_format(self):
        ts = _make_toolset()
        result = ts.generate_report(findings=[], format="xml", output_path="/tmp/report.xml")
        assert result["status"] == "error"
        assert "Unsupported format" in result.get("error", "")

    def test_empty_findings(self):
        ts = _make_toolset()
        result = ts.generate_report(findings=[], format="json", output_path="/tmp/report.json")
        assert result["status"] == "ok"
        assert result["report_summary"]["total_findings"] == 0


# ---------------------------------------------------------------------------
# A-7 audit_check_compliance_template
# ---------------------------------------------------------------------------

class TestCheckComplianceTemplate:

    def test_owasp_top_10(self):
        ts = _make_toolset()
        result = ts.check_compliance_template(path="src/app.py", template="owasp_top_10", workspace_root="/tmp")
        assert result["status"] == "ok"
        assert result["template"] == "owasp_top_10"
        assert len(result["checks"]) == 10
        assert result["pass_count"] + result["fail_count"] == len(result["checks"])

    def test_cwe(self):
        ts = _make_toolset()
        result = ts.check_compliance_template(path="src/app.py", template="cwe", workspace_root="/tmp")
        assert result["status"] == "ok"
        assert result["template"] == "cwe"
        assert len(result["checks"]) >= 1
        assert result["pass_count"] + result["fail_count"] == len(result["checks"])

    def test_invalid_template(self):
        ts = _make_toolset()
        result = ts.check_compliance_template(path="src/app.py", template="iso27001", workspace_root="/tmp")
        assert result["status"] == "error"
        assert "Unknown template" in result.get("error", "")


# ---------------------------------------------------------------------------
# A-8 audit_ci_summary
# ---------------------------------------------------------------------------

class TestCISummary:

    def test_pass_exit_code(self):
        ts = _make_toolset()
        findings = [{"id": "F1", "severity": "low", "title": "Lint"}]
        result = ts.ci_summary(findings=findings, severity_threshold="high")
        assert result["exit_code"] == 0
        assert result["total_findings"] == 1

    def test_fail_exit_code(self):
        ts = _make_toolset()
        findings = [{"id": "F1", "severity": "high", "title": "SQLi"}]
        result = ts.ci_summary(findings=findings, severity_threshold="high")
        assert result["exit_code"] == 1

    def test_critical_threshold(self):
        ts = _make_toolset()
        findings = [
            {"id": "F1", "severity": "critical", "title": "RCE"},
            {"id": "F2", "severity": "high", "title": "SQLi"},
        ]
        result = ts.ci_summary(findings=findings, severity_threshold="critical")
        assert result["exit_code"] == 1
        assert result["by_severity"]["critical"] == 1

    def test_empty_findings_pass(self):
        ts = _make_toolset()
        result = ts.ci_summary(findings=[], severity_threshold="low")
        assert result["exit_code"] == 0
        assert result["total_findings"] == 0

    def test_invalid_threshold(self):
        ts = _make_toolset()
        result = ts.ci_summary(findings=[], severity_threshold="blocker")
        assert result["exit_code"] == 1


# ---------------------------------------------------------------------------
# A-9 audit_deduplicate_findings
# ---------------------------------------------------------------------------

class TestDeduplicateFindings:

    def test_dedup_by_explicit_fingerprint(self):
        ts = _make_toolset()
        findings = [
            {"id": "F1", "fingerprint": "abc", "severity": "high", "title": "SQLi"},
            {"id": "F2", "fingerprint": "abc", "severity": "medium", "title": "SQLi variant"},
        ]
        result = ts.deduplicate_findings(findings=findings)
        assert result["original_count"] == 2
        assert result["deduplicated_count"] == 1
        # Should keep higher severity
        assert result["findings"][0]["severity"] == "high"

    def test_dedup_derives_fingerprint(self):
        ts = _make_toolset()
        findings = [
            {"id": "F1", "file": "a.py", "line": 10, "severity": "low"},
            {"id": "F1", "file": "a.py", "line": 10, "severity": "low"},
        ]
        result = ts.deduplicate_findings(findings=findings)
        assert result["original_count"] == 2
        assert result["deduplicated_count"] == 1

    def test_no_dedup_when_different(self):
        ts = _make_toolset()
        findings = [
            {"id": "F1", "fingerprint": "a", "severity": "high"},
            {"id": "F2", "fingerprint": "b", "severity": "medium"},
        ]
        result = ts.deduplicate_findings(findings=findings)
        assert result["deduplicated_count"] == 2

    def test_empty_findings(self):
        ts = _make_toolset()
        result = ts.deduplicate_findings(findings=[])
        assert result["original_count"] == 0
        assert result["deduplicated_count"] == 0
        assert result["findings"] == []


# ---------------------------------------------------------------------------
# A-10 audit_track_remediation
# ---------------------------------------------------------------------------

class TestTrackRemediation:

    def test_open_status(self):
        ts = _make_toolset()
        result = ts.track_remediation(finding_id="F1", status="open", workspace_root="/tmp")
        assert result["finding_id"] == "F1"
        assert result["status"] == "open"
        assert "updated_at" in result

    def test_fixed_status(self):
        ts = _make_toolset()
        result = ts.track_remediation(finding_id="F2", status="fixed", workspace_root="/tmp")
        assert result["status"] == "fixed"

    def test_accepted_risk_status(self):
        ts = _make_toolset()
        result = ts.track_remediation(finding_id="F3", status="accepted_risk", workspace_root="/tmp")
        assert result["status"] == "accepted_risk"

    def test_invalid_status(self):
        ts = _make_toolset()
        result = ts.track_remediation(finding_id="F4", status="wontfix", workspace_root="/tmp")
        assert result["status"] == "error"
        assert "Invalid status" in result.get("error", "")

    def test_update_overwrite(self):
        ts = _make_toolset()
        ts.track_remediation(finding_id="F5", status="open", workspace_root="/tmp")
        result = ts.track_remediation(finding_id="F5", status="fixed", workspace_root="/tmp")
        assert result["status"] == "fixed"


# ---------------------------------------------------------------------------
# AuditFinding dataclass
# ---------------------------------------------------------------------------

class TestAuditFinding:

    def test_creation_and_to_dict(self):
        from qitos_zoo.qitos_auditor import AuditFinding

        f = AuditFinding(
            id="F1", title="SQLi", severity="high",
            file="app.py", line=42, description="SQL injection", status="open",
        )
        d = f.to_dict()
        assert d["id"] == "F1"
        assert d["title"] == "SQLi"
        assert d["severity"] == "high"
        assert d["file"] == "app.py"
        assert d["line"] == 42
        assert d["description"] == "SQL injection"
        assert d["status"] == "open"

    def test_defaults(self):
        from qitos_zoo.qitos_auditor import AuditFinding

        f = AuditFinding(id="F2", title="Typo", severity="low", file="a.py", line=1)
        assert f.description == ""
        assert f.status == "open"


# ---------------------------------------------------------------------------
# AuditReport dataclass
# ---------------------------------------------------------------------------

class TestAuditReport:

    def test_to_dict(self):
        from qitos_zoo.qitos_auditor import AuditFinding, AuditReport

        findings = [
            AuditFinding(id="F1", title="SQLi", severity="high", file="a.py", line=10),
            AuditFinding(id="F2", title="Typo", severity="low", file="b.py", line=5),
        ]
        report = AuditReport(findings=findings, format="json")
        d = report.to_dict()
        assert d["format"] == "json"
        assert d["summary"]["total_findings"] == 2
        assert d["summary"]["by_severity"]["high"] == 1
        assert d["summary"]["by_severity"]["low"] == 1
        assert len(d["findings"]) == 2
        assert "generated_at" in d

    def test_empty_report(self):
        from qitos_zoo.qitos_auditor import AuditReport

        report = AuditReport()
        d = report.to_dict()
        assert d["summary"]["total_findings"] == 0
        assert d["findings"] == []


# ---------------------------------------------------------------------------
# Tool markers (read_only / needs_approval)
# ---------------------------------------------------------------------------

class TestToolMarkers:

    def test_all_tool_markers(self):
        from qitos_zoo.qitos_auditor.tools.audit_toolset import AuditToolSet
        from qitos.core.tool import FunctionTool

        with tempfile.TemporaryDirectory() as tmp:
            ts = AuditToolSet(workspace_root=tmp)
            tools = ts.tools()
            assert len(tools) == 11

            needs_approval_names = {
                "audit_report_findings",
                "audit_generate_report",
                "audit_track_remediation",
                "audit_index_knowledge",
            }
            read_only_names = {
                "audit_scan_patterns",
                "audit_check_compliance",
                "audit_suggest_fix",
                "audit_check_compliance_template",
                "audit_ci_summary",
                "audit_deduplicate_findings",
                "audit_search_knowledge",
            }

            for tool in tools:
                assert isinstance(tool, FunctionTool)
                name = tool.spec.name
                if name in needs_approval_names:
                    assert tool.spec.needs_approval is True, f"{name} should need approval"
                elif name in read_only_names:
                    assert tool.spec.read_only is True, f"{name} should be read_only"
