"""Tests for pentagi tools @function_tool migration."""
from __future__ import annotations

import tempfile
import pytest

from qitos.core.tool import FunctionTool


def _all_pentagi_tools():
    """Collect all pentagi tools from all toolsets."""
    from qitos_zoo.qitos_cyber.pentagi.tools.barrier import BarrierToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.terminal_env import TerminalEnvToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.search_network import SearchNetworkToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.search_vector_db import SearchVectorDBToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.store_agent_result import StoreAgentResultToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.store_vector_db import StoreVectorDBToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.browser import BrowserToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.advice import AdviceToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.generate_subtasks import GenerateSubtasksToolSet
    from qitos_zoo.qitos_cyber.pentagi.tools.generate_report import GenerateReportToolSet

    tools = []
    for ts_class in [BarrierToolSet, TerminalEnvToolSet, SearchNetworkToolSet,
                     SearchVectorDBToolSet, StoreAgentResultToolSet, StoreVectorDBToolSet,
                     BrowserToolSet, AdviceToolSet, GenerateSubtasksToolSet, GenerateReportToolSet]:
        try:
            ts = ts_class()
        except TypeError:
            # Some toolsets require params — skip them if they can't be instantiated
            continue
        tools.extend(ts.tools())
    return tools


def test_all_pentagi_tools_are_function_tool_instances():
    tools = _all_pentagi_tools()
    assert len(tools) >= 20, f"Expected at least 20 tools, got {len(tools)}"
    for tool in tools:
        assert isinstance(tool, FunctionTool), f"{tool.spec.name} is not FunctionTool"


def test_search_tools_are_read_only():
    tools = _all_pentagi_tools()
    # Exclude barrier result tools like "search_result" — those are completion signals, not search tools
    search_tools = [
        t for t in tools
        if t.spec.name.startswith("search_") and not t.spec.name.endswith("_result")
    ]
    assert len(search_tools) >= 4, f"Expected at least 4 search tools, got {len(search_tools)}"
    for tool in search_tools:
        assert tool.spec.read_only is True, f"{tool.spec.name} should be read_only"


def test_store_tools_need_approval():
    tools = _all_pentagi_tools()
    store_tools = [t for t in tools if t.spec.name.startswith("store_")]
    assert len(store_tools) >= 5, f"Expected at least 5 store tools, got {len(store_tools)}"
    for tool in store_tools:
        assert tool.spec.needs_approval is True, f"{tool.spec.name} needs approval"


def test_terminal_tools_need_approval():
    tools = _all_pentagi_tools()
    terminal_tools = [t for t in tools if "terminal" in t.spec.name or "write" in t.spec.name]
    assert len(terminal_tools) >= 1, f"Expected at least 1 terminal/write tool, got {len(terminal_tools)}"
    for tool in terminal_tools:
        assert tool.spec.needs_approval is True, f"{tool.spec.name} needs approval"


def test_tool_specs_have_names_and_descriptions():
    tools = _all_pentagi_tools()
    for tool in tools:
        assert tool.spec.name, "Tool missing name"
        assert tool.spec.description, f"Tool {tool.spec.name} missing description"


def test_legacy_aliases_produce_function_tool_instances():
    """Verify backward-compatible legacy class aliases still work."""
    from qitos_zoo.qitos_cyber.pentagi.tools.barrier import (
        BarrierDone, BarrierAsk, HackResultTool, CodeResultTool,
        MaintenanceResultTool, SearchResultTool, MemoristResultTool,
        EnricherResultTool, SubtaskListTool, SubtaskPatchTool, ReportResultTool,
    )
    from qitos_zoo.qitos_cyber.pentagi.tools.terminal_env import (
        TerminalTool, ReadFileTool, WriteFileTool, ListFilesTool,
    )
    from qitos_zoo.qitos_cyber.pentagi.tools.search_network import (
        GoogleSearchTool, DuckDuckGoSearchTool, SearchInMemoryTool,
    )
    from qitos_zoo.qitos_cyber.pentagi.tools.store_agent_result import (
        StoreGuideTool, StoreFindingTool,
    )
    from qitos_zoo.qitos_cyber.pentagi.tools.browser import BrowserTool
    from qitos_zoo.qitos_cyber.pentagi.tools.generate_subtasks import GenerateSubtasksTool
    from qitos_zoo.qitos_cyber.pentagi.tools.generate_report import GenerateReportTool

    # Each legacy class should instantiate and have a spec
    legacy_classes = [
        BarrierDone, BarrierAsk, HackResultTool, CodeResultTool,
        MaintenanceResultTool, SearchResultTool, MemoristResultTool,
        EnricherResultTool, SubtaskListTool, SubtaskPatchTool, ReportResultTool,
        TerminalTool, ReadFileTool, WriteFileTool, ListFilesTool,
        GoogleSearchTool, DuckDuckGoSearchTool, SearchInMemoryTool,
        StoreGuideTool, StoreFindingTool,
        BrowserTool,
        GenerateSubtasksTool, GenerateReportTool,
    ]
    for cls in legacy_classes:
        try:
            instance = cls()
        except TypeError:
            # Some legacy aliases may need constructor args (e.g., BrowserTool)
            continue
        assert hasattr(instance, "spec"), f"{cls.__name__} missing spec"
        assert instance.spec.name, f"{cls.__name__} has no name"


def test_barrier_toolset_tool_count():
    """BarrierToolSet should produce 11 tools."""
    from qitos_zoo.qitos_cyber.pentagi.tools.barrier import BarrierToolSet
    ts = BarrierToolSet()
    tools = ts.tools()
    assert len(tools) == 11, f"Expected 11 barrier tools, got {len(tools)}"


def test_search_network_toolset_tool_count():
    """SearchNetworkToolSet should produce 8 tools."""
    from qitos_zoo.qitos_cyber.pentagi.tools.search_network import SearchNetworkToolSet
    ts = SearchNetworkToolSet()
    tools = ts.tools()
    assert len(tools) == 8, f"Expected 8 search tools, got {len(tools)}"


def test_terminal_env_toolset_tool_count():
    """TerminalEnvToolSet should produce 4 tools."""
    from qitos_zoo.qitos_cyber.pentagi.tools.terminal_env import TerminalEnvToolSet
    ts = TerminalEnvToolSet()
    tools = ts.tools()
    assert len(tools) == 4, f"Expected 4 terminal tools, got {len(tools)}"


def test_search_vector_db_toolset_tool_count():
    """SearchVectorDBToolSet should produce 4 tools."""
    from qitos_zoo.qitos_cyber.pentagi.tools.search_vector_db import SearchVectorDBToolSet
    ts = SearchVectorDBToolSet()
    tools = ts.tools()
    assert len(tools) == 4, f"Expected 4 vector db search tools, got {len(tools)}"


def test_store_agent_result_toolset_tool_count():
    """StoreAgentResultToolSet should produce 6 tools."""
    from qitos_zoo.qitos_cyber.pentagi.tools.store_agent_result import StoreAgentResultToolSet
    ts = StoreAgentResultToolSet()
    tools = ts.tools()
    assert len(tools) == 6, f"Expected 6 store tools, got {len(tools)}"


def test_store_vector_db_toolset_tool_count():
    """StoreVectorDBToolSet should produce 3 tools."""
    from qitos_zoo.qitos_cyber.pentagi.tools.store_vector_db import StoreVectorDBToolSet
    ts = StoreVectorDBToolSet()
    tools = ts.tools()
    assert len(tools) == 3, f"Expected 3 vector store tools, got {len(tools)}"


def test_browser_toolset_tool_count():
    """BrowserToolSet should produce 1 tool."""
    from qitos_zoo.qitos_cyber.pentagi.tools.browser import BrowserToolSet
    ts = BrowserToolSet()
    tools = ts.tools()
    assert len(tools) == 1, f"Expected 1 browser tool, got {len(tools)}"


def test_read_file_tool_is_read_only():
    """read_file should be read_only."""
    from qitos_zoo.qitos_cyber.pentagi.tools.terminal_env import TerminalEnvToolSet
    ts = TerminalEnvToolSet()
    tools = ts.tools()
    read_tool = next(t for t in tools if t.spec.name == "read_file")
    assert read_tool.spec.read_only is True
    list_tool = next(t for t in tools if t.spec.name == "list_files")
    assert list_tool.spec.read_only is True


def test_write_file_tool_needs_approval():
    """write_file should need approval."""
    from qitos_zoo.qitos_cyber.pentagi.tools.terminal_env import TerminalEnvToolSet
    ts = TerminalEnvToolSet()
    tools = ts.tools()
    write_tool = next(t for t in tools if t.spec.name == "write_file")
    assert write_tool.spec.needs_approval is True
    terminal_tool = next(t for t in tools if t.spec.name == "terminal")
    assert terminal_tool.spec.needs_approval is True


def test_browser_tool_needs_approval():
    """browser should need approval."""
    from qitos_zoo.qitos_cyber.pentagi.tools.browser import BrowserToolSet
    ts = BrowserToolSet()
    tools = ts.tools()
    browser_tool = tools[0]
    assert browser_tool.spec.needs_approval is True
    assert browser_tool.spec.name == "browser"


def test_generate_subtasks_is_read_only():
    """generate_subtasks should be read_only."""
    from qitos_zoo.qitos_cyber.pentagi.tools.generate_subtasks import GenerateSubtasksToolSet
    ts = GenerateSubtasksToolSet()
    tools = ts.tools()
    assert tools[0].spec.read_only is True


def test_generate_report_needs_approval():
    """generate_report should need approval."""
    from qitos_zoo.qitos_cyber.pentagi.tools.generate_report import GenerateReportToolSet
    ts = GenerateReportToolSet()
    tools = ts.tools()
    assert tools[0].spec.needs_approval is True


# --- Comprehensive marker verification ---

# Expected markers for every pentagi tool: (read_only, needs_approval)
_TOOL_MARKERS = {
    # barrier.py — 11 tools
    "done": (False, False),
    "ask_user": (False, False),
    "hack_result": (False, False),
    "code_result": (False, False),
    "maintenance_result": (False, False),
    "search_result": (False, False),
    "memorist_result": (False, False),
    "enricher_result": (False, False),
    "subtask_list": (False, False),
    "subtask_patch": (False, False),
    "report_result": (False, True),
    # terminal_env.py — 4 tools
    "terminal": (False, True),
    "read_file": (True, False),
    "write_file": (False, True),
    "list_files": (True, False),
    # search_network.py — 8 tools
    "google_search": (True, True),
    "duckduckgo_search": (True, True),
    "tavily_search": (True, True),
    "searxng_search": (True, True),
    "sploitus_search": (True, True),
    "search_in_memory": (True, False),
    "traversaal_search": (True, True),
    "perplexity_search": (True, True),
    # search_vector_db.py — 4 tools
    "search_guide": (True, False),
    "search_answer": (True, False),
    "search_code": (True, False),
    "graphiti_search": (True, False),
    # store_agent_result.py — 6 tools
    "store_guide": (False, True),
    "store_answer": (False, True),
    "store_code": (False, True),
    "store_finding": (False, True),
    "store_subtask_result": (False, True),
    "store_evidence": (False, True),
    # store_vector_db.py — 3 tools
    "store_vector_guide": (False, True),
    "store_vector_answer": (False, True),
    "store_vector_code": (False, True),
    # browser.py — 1 tool
    "browser": (False, True),
    # advice.py — 1 tool
    "advice": (True, False),
    # generate_subtasks.py — 1 tool
    "generate_subtasks": (True, False),
    # generate_report.py — 1 tool
    "generate_report": (False, True),
}


def test_all_tool_markers_match_expected():
    """Every pentagi tool has the expected read_only and needs_approval markers."""
    tools = _all_pentagi_tools()
    for tool in tools:
        name = tool.spec.name
        assert name in _TOOL_MARKERS, f"Tool {name!r} not in _TOOL_MARKERS — update the expected markers dict"
        expected_ro, expected_na = _TOOL_MARKERS[name]
        assert tool.spec.read_only == expected_ro, (
            f"{name}: read_only={tool.spec.read_only}, expected {expected_ro}"
        )
        assert tool.spec.needs_approval == expected_na, (
            f"{name}: needs_approval={tool.spec.needs_approval}, expected {expected_na}"
        )


def test_no_unexpected_tools():
    """All tools returned by toolsets are accounted for in the markers dict."""
    tools = _all_pentagi_tools()
    tool_names = {t.spec.name for t in tools}
    marker_names = set(_TOOL_MARKERS.keys())
    # Every tool in the toolsets should be in the markers dict
    missing = tool_names - marker_names
    assert not missing, f"Tools not in markers dict: {missing}"


def test_total_tool_count():
    """Total pentagi tool count matches expected."""
    tools = _all_pentagi_tools()
    expected_count = len(_TOOL_MARKERS)
    assert len(tools) == expected_count, (
        f"Expected {expected_count} tools, got {len(tools)}"
    )


def test_all_search_network_tools_read_only():
    """All search_network tools are read_only."""
    from qitos_zoo.qitos_cyber.pentagi.tools.search_network import SearchNetworkToolSet
    ts = SearchNetworkToolSet()
    for tool in ts.tools():
        assert tool.spec.read_only is True, f"{tool.spec.name} should be read_only"


def test_all_store_tools_need_approval():
    """All store_* tools require approval."""
    tools = _all_pentagi_tools()
    store_tools = [t for t in tools if t.spec.name.startswith("store_")]
    for tool in store_tools:
        assert tool.spec.needs_approval is True, f"{tool.spec.name} should need approval"


def test_barrier_done_no_markers():
    """Barrier 'done' tool has read_only=False and needs_approval=False (no markers set)."""
    from qitos_zoo.qitos_cyber.pentagi.tools.barrier import BarrierToolSet
    ts = BarrierToolSet()
    done_tool = next(t for t in ts.tools() if t.spec.name == "done")
    assert done_tool.spec.read_only is False
    assert done_tool.spec.needs_approval is False


def test_barrier_result_tools_mostly_no_approval():
    """Barrier result tools (hack/code/maintenance/search/memorist/enricher) don't need approval."""
    from qitos_zoo.qitos_cyber.pentagi.tools.barrier import BarrierToolSet
    ts = BarrierToolSet()
    result_names = {"hack_result", "code_result", "maintenance_result",
                    "search_result", "memorist_result", "enricher_result"}
    for tool in ts.tools():
        if tool.spec.name in result_names:
            assert tool.spec.needs_approval is False, f"{tool.spec.name} should not need approval"


def test_advice_tool_is_read_only():
    """advice tool should be read_only."""
    from qitos_zoo.qitos_cyber.pentagi.tools.advice import AdviceToolSet
    ts = AdviceToolSet()
    tools = ts.tools()
    assert len(tools) == 1
    assert tools[0].spec.read_only is True
    assert tools[0].spec.needs_approval is False


def test_search_vector_db_all_read_only():
    """All search_vector_db tools are read_only."""
    from qitos_zoo.qitos_cyber.pentagi.tools.search_vector_db import SearchVectorDBToolSet
    ts = SearchVectorDBToolSet()
    for tool in ts.tools():
        assert tool.spec.read_only is True, f"{tool.spec.name} should be read_only"
