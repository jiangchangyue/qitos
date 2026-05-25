"""Tests for CacheInterceptor LRU eviction."""
from __future__ import annotations

from qitos.core.action import Action, ActionResult, ActionStatus
from qitos.core.interceptor import InterceptorContext
from qitos.kit.interceptor.cache import CacheInterceptor


def _make_action(name: str = "read_file", args: dict | None = None) -> Action:
    return Action(name=name, args=args or {"path": "test.py"}, kind="tool")


def _make_result(name: str = "read_file", output: str = "ok") -> ActionResult:
    return ActionResult(name=name, status=ActionStatus.SUCCESS, output=output)


def _make_context(
    tool_name: str = "read_file",
    read_only: bool = False,
) -> InterceptorContext:
    """Create a minimal InterceptorContext with a mock tool registry."""
    from unittest.mock import MagicMock

    from qitos.core.tool import ToolSpec

    spec = ToolSpec(name=tool_name, description="read")
    spec.read_only = read_only

    tool = MagicMock()
    tool.spec = spec

    registry = MagicMock()
    registry.get.return_value = tool

    state = MagicMock()
    state.tool_registry = registry

    return InterceptorContext(
        tool_name=tool_name,
        tool_args={"path": "test.py"},
        step_id=0,
        state=state,
    )


def test_lru_evicts_least_recently_used():
    """When cache is full, the least recently accessed entry is evicted."""
    cache = CacheInterceptor(max_size=3)

    # Insert 3 entries
    for i in range(3):
        action = _make_action(f"tool_{i}")
        ctx = _make_context(tool_name=f"tool_{i}", read_only=True)
        result = _make_result(f"tool_{i}", f"result_{i}")

        action_meta = cache.before_execute(action, ctx)
        cache.after_execute(action_meta, result, ctx)

    # Access tool_0 (making it recently used)
    action = _make_action("tool_0")
    ctx = _make_context(tool_name="tool_0", read_only=True)
    action_meta = cache.before_execute(action, ctx)
    # Simulate cache hit
    result = _make_result("tool_0", "result_0")
    cache.after_execute(action_meta, result, ctx)

    # Insert new entry — should evict tool_1 (LRU), not tool_0
    action = _make_action("tool_3")
    ctx = _make_context(tool_name="tool_3", read_only=True)
    result = _make_result("tool_3", "result_3")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    # tool_0 should still be cached (was accessed), tool_1 should be evicted
    assert ("tool_0", frozenset({"path": "test.py"}.items())) in cache._cache
    assert ("tool_1", frozenset({"path": "test.py"}.items())) not in cache._cache
    assert ("tool_2", frozenset({"path": "test.py"}.items())) in cache._cache
    assert ("tool_3", frozenset({"path": "test.py"}.items())) in cache._cache


def test_set_overwrite_updates_access_order():
    """Overwriting an existing key updates its access order."""
    cache = CacheInterceptor(max_size=2)

    # Insert tool_0 and tool_1
    for i in range(2):
        action = _make_action(f"tool_{i}")
        ctx = _make_context(tool_name=f"tool_{i}", read_only=True)
        result = _make_result(f"tool_{i}", f"result_{i}")
        action_meta = cache.before_execute(action, ctx)
        cache.after_execute(action_meta, result, ctx)

    # Overwrite tool_0 with new result
    action = _make_action("tool_0")
    ctx = _make_context(tool_name="tool_0", read_only=True)
    result = _make_result("tool_0", "result_0_v2")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    # Insert new entry — should evict tool_1 (not tool_0, since tool_0 was just updated)
    action = _make_action("tool_2")
    ctx = _make_context(tool_name="tool_2", read_only=True)
    result = _make_result("tool_2", "result_2")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    assert ("tool_0", frozenset({"path": "test.py"}.items())) in cache._cache
    assert ("tool_1", frozenset({"path": "test.py"}.items())) not in cache._cache


def test_get_hit_updates_access_order():
    """Cache hits on get update access order."""
    cache = CacheInterceptor(max_size=2)

    # Insert tool_0 and tool_1
    for i in range(2):
        action = _make_action(f"tool_{i}")
        ctx = _make_context(tool_name=f"tool_{i}", read_only=True)
        result = _make_result(f"tool_{i}", f"result_{i}")
        action_meta = cache.before_execute(action, ctx)
        cache.after_execute(action_meta, result, ctx)

    # Access tool_0 via cache hit (before_execute marks _cache_hit, after_execute returns cached)
    action = _make_action("tool_0")
    ctx = _make_context(tool_name="tool_0", read_only=True)
    action_meta = cache.before_execute(action, ctx)
    # The after_execute will detect cache_hit=True and return cached result + touch
    result = _make_result("tool_0", "result_0")
    cache.after_execute(action_meta, result, ctx)

    # Insert new — should evict tool_1 not tool_0
    action = _make_action("tool_2")
    ctx = _make_context(tool_name="tool_2", read_only=True)
    result = _make_result("tool_2", "result_2")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    assert ("tool_0", frozenset({"path": "test.py"}.items())) in cache._cache
    assert ("tool_1", frozenset({"path": "test.py"}.items())) not in cache._cache


def test_max_size_one_boundary():
    """LRU works correctly with max_size=1."""
    cache = CacheInterceptor(max_size=1)

    action = _make_action("tool_0")
    ctx = _make_context(tool_name="tool_0", read_only=True)
    result = _make_result("tool_0", "result_0")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    assert len(cache._cache) == 1

    action = _make_action("tool_1")
    ctx = _make_context(tool_name="tool_1", read_only=True)
    result = _make_result("tool_1", "result_1")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    assert len(cache._cache) == 1
    assert ("tool_0", frozenset({"path": "test.py"}.items())) not in cache._cache
    assert ("tool_1", frozenset({"path": "test.py"}.items())) in cache._cache


def test_clear_resets_lru_state():
    """clear() resets both cache and access order."""
    cache = CacheInterceptor(max_size=2)

    for i in range(2):
        action = _make_action(f"tool_{i}")
        ctx = _make_context(tool_name=f"tool_{i}", read_only=True)
        result = _make_result(f"tool_{i}", f"result_{i}")
        action_meta = cache.before_execute(action, ctx)
        cache.after_execute(action_meta, result, ctx)

    cache.clear()
    assert len(cache._cache) == 0
    assert len(cache._insertion_order) == 0


def test_non_read_only_tools_not_cached():
    """Non-read-only tools should not be cached."""
    cache = CacheInterceptor(max_size=10)

    action = _make_action("write_file")
    ctx = _make_context(tool_name="write_file", read_only=False)
    result = _make_result("write_file", "written")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    assert len(cache._cache) == 0


def test_fifo_behavior_preserved_without_access():
    """Without any re-access, eviction follows insertion order (same as FIFO)."""
    cache = CacheInterceptor(max_size=3)

    for i in range(4):
        action = _make_action(f"tool_{i}")
        ctx = _make_context(tool_name=f"tool_{i}", read_only=True)
        result = _make_result(f"tool_{i}", f"result_{i}")
        action_meta = cache.before_execute(action, ctx)
        cache.after_execute(action_meta, result, ctx)

    # tool_0 should be evicted (first inserted, never accessed)
    assert ("tool_0", frozenset({"path": "test.py"}.items())) not in cache._cache
    # tool_1, tool_2, tool_3 should remain
    for i in range(1, 4):
        assert (f"tool_{i}", frozenset({"path": "test.py"}.items())) in cache._cache


def test_duplicate_insert_does_not_bloat_order():
    """Inserting the same key twice should not add duplicate entries to _insertion_order."""
    cache = CacheInterceptor(max_size=10)

    action = _make_action("tool_0")
    ctx = _make_context(tool_name="tool_0", read_only=True)

    result = _make_result("tool_0", "result_0")
    action_meta = cache.before_execute(action, ctx)
    cache.after_execute(action_meta, result, ctx)

    # Re-insert same tool
    result2 = _make_result("tool_0", "result_0_v2")
    action_meta2 = cache.before_execute(action, ctx)
    cache.after_execute(action_meta2, result2, ctx)

    # _insertion_order should only have one entry for this key
    key = ("tool_0", frozenset({"path": "test.py"}.items()))
    assert cache._insertion_order.count(key) == 1
