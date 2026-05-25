"""Tests for auditor knowledge system (A-8) and AuditBoardMemory integration."""
from __future__ import annotations

from unittest.mock import MagicMock

from qitos.core.memory import MemoryRecord


# ---------------------------------------------------------------------------
# AuditBoardMemory tests
# ---------------------------------------------------------------------------


def test_audit_board_memory_basic_operations():
    """AuditBoardMemory supports append and retrieve."""
    from qitos_zoo.qitos_auditor.memory import AuditBoardMemory
    mem = AuditBoardMemory()
    rec = MemoryRecord(role="finding", content="SQL injection in query", step_id=1, metadata={"id": "f1"})
    mem.append(rec)
    results = mem.retrieve({"max_items": 10})
    assert len(results) == 1
    assert results[0].content == "SQL injection in query"


def test_audit_board_memory_role_filtering():
    """AuditBoardMemory filters by role."""
    from qitos_zoo.qitos_auditor.memory import AuditBoardMemory
    mem = AuditBoardMemory()
    mem.append(MemoryRecord(role="finding", content="SQL injection", step_id=1, metadata={"id": "f1"}))
    mem.append(MemoryRecord(role="hotspot", content="Entry point main.py", step_id=1, metadata={"id": "h1"}))
    findings = mem.retrieve({"roles": ["finding"]})
    assert len(findings) == 1
    assert findings[0].role == "finding"


def test_audit_board_memory_ingest_finding():
    """AuditBoardMemory.ingest_finding adds to confirmed_findings board."""
    from qitos_zoo.qitos_auditor.memory import AuditBoardMemory
    mem = AuditBoardMemory()
    mem.ingest_finding(
        {"title": "XSS vulnerability", "file": "app.py", "line": 42, "description": "Reflected XSS"},
        step_id=1,
    )
    snap = mem.snapshot()
    assert len(snap["confirmed_findings"]) == 1
    assert snap["confirmed_findings"][0]["title"] == "XSS vulnerability"


def test_audit_board_memory_with_vector_memory():
    """AuditBoardMemory with VectorMemory enables semantic search."""
    from qitos_zoo.qitos_auditor.memory import AuditBoardMemory
    from qitos.kit.memory.vector_memory import VectorMemory
    vm = VectorMemory()  # Uses hash embedder by default
    mem = AuditBoardMemory(vector_memory=vm)
    mem.append(MemoryRecord(role="finding", content="SQL injection in login query", step_id=1, metadata={"id": "f1", "audit_role": "finding"}))
    mem.append(MemoryRecord(role="finding", content="XSS reflected in search page", step_id=2, metadata={"id": "f2", "audit_role": "finding"}))

    # Vector mode retrieval
    results = mem.retrieve({"mode": "vector", "text": "SQL injection", "top_k": 1})
    assert len(results) >= 1


def test_audit_board_memory_without_vector_graceful():
    """AuditBoardMemory without VectorMemory falls back to rule-based."""
    from qitos_zoo.qitos_auditor.memory import AuditBoardMemory
    mem = AuditBoardMemory()
    mem.append(MemoryRecord(role="finding", content="test finding", step_id=1, metadata={"id": "f1"}))
    # Vector mode without vector_memory returns empty (graceful degradation)
    results = mem.retrieve({"mode": "vector", "text": "test"})
    assert results == []


# ---------------------------------------------------------------------------
# AuditRecord tests
# ---------------------------------------------------------------------------


def test_audit_record_auto_id():
    """AuditRecord generates an id if not provided."""
    from qitos_zoo.qitos_auditor.memory import AuditRecord
    rec = AuditRecord(content="test", role="finding")
    assert rec.id  # Not empty


def test_audit_record_to_memory_record():
    """AuditRecord converts to MemoryRecord."""
    from qitos_zoo.qitos_auditor.memory import AuditRecord
    rec = AuditRecord(id="f1", content="test finding", role="finding", metadata={"file": "a.py"})
    mr = rec.to_memory_record()
    assert mr.role == "finding"
    assert mr.content == "test finding"
    assert mr.metadata["id"] == "f1"
    assert mr.metadata["audit_role"] == "finding"


# ---------------------------------------------------------------------------
# AuditToolSet knowledge tools
# ---------------------------------------------------------------------------


def test_search_knowledge_without_memory():
    """audit_search_knowledge returns gracefully when no memory configured."""
    from qitos_zoo.qitos_auditor.tools.audit_toolset import AuditToolSet
    ts = AuditToolSet(workspace_root=".")
    result = ts.search_knowledge(query="SQL injection")
    assert result["status"] == "ok"
    assert result["results"] == []


def test_index_knowledge_without_memory():
    """audit_index_knowledge returns error when no memory configured."""
    from qitos_zoo.qitos_auditor.tools.audit_toolset import AuditToolSet
    ts = AuditToolSet(workspace_root=".")
    result = ts.index_knowledge(content="test finding", role="finding")
    assert result["status"] == "error"


def test_search_and_index_knowledge_with_memory():
    """audit_search_knowledge and audit_index_knowledge work with memory."""
    from qitos_zoo.qitos_auditor.tools.audit_toolset import AuditToolSet
    from qitos_zoo.qitos_auditor.memory import AuditBoardMemory
    mem = AuditBoardMemory()
    ts = AuditToolSet(workspace_root=".", memory=mem)

    # Index some content
    idx_result = ts.index_knowledge(content="SQL injection in login query at app.py:42", role="finding")
    assert idx_result["status"] == "ok"
    assert idx_result["role"] == "finding"

    # Search for it
    search_result = ts.search_knowledge(query="SQL injection", top_k=5)
    assert search_result["status"] == "ok"
    assert search_result["total"] >= 1


# ---------------------------------------------------------------------------
# AuditAgent integration
# ---------------------------------------------------------------------------


def test_audit_agent_accepts_memory():
    """AuditAgent accepts memory parameter."""
    from qitos_zoo.qitos_auditor import AuditAgent, AuditBoardMemory
    mem = AuditBoardMemory()
    agent = AuditAgent(llm=MagicMock(), workspace_root=".", memory=mem)
    assert agent._audit_memory is mem


def test_audit_agent_accepts_embedder():
    """AuditAgent accepts embedder and creates AuditBoardMemory with VectorMemory."""
    from qitos_zoo.qitos_auditor import AuditAgent
    agent = AuditAgent(llm=MagicMock(), workspace_root=".", embedder=lambda x: [0.1] * 16)
    assert agent._audit_memory is not None
    assert agent._audit_memory._vector_memory is not None


def test_audit_agent_no_memory():
    """AuditAgent works without memory or embedder."""
    from qitos_zoo.qitos_auditor import AuditAgent
    agent = AuditAgent(llm=MagicMock(), workspace_root=".")
    assert agent._audit_memory is None
