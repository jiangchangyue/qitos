"""CacheInterceptor -- cache read-only tool call results."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ...core.action import Action, ActionResult, ActionStatus
from ...core.interceptor import InterceptorContext, ToolInterceptor
from ...core.tool import BaseTool


class CacheInterceptor(ToolInterceptor):
    """Cache results from read-only tool calls.

    Uses a simple dict-based cache keyed by ``(tool_name, frozenset(args.items()))``.
    Only caches results whose tool spec has ``read_only=True``.

    Parameters:
        max_size: Maximum number of cached entries (default 128).  When the
            cache exceeds this size, the least recently used entry is evicted (LRU).
    """

    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._cache: Dict[Tuple[str, frozenset], ActionResult] = {}
        self._insertion_order: list[Tuple[str, frozenset]] = []

    @staticmethod
    def _cache_key(tool_name: str, args: Dict[str, Any]) -> Tuple[str, frozenset]:
        return (tool_name, frozenset(args.items()))

    def _touch(self, key: Tuple[str, frozenset]) -> None:
        """Move key to end of insertion order (LRU access update)."""
        try:
            self._insertion_order.remove(key)
        except ValueError:
            pass
        self._insertion_order.append(key)

    def _is_read_only(self, tool_name: str, context: InterceptorContext) -> bool:
        """Check if the tool is read-only via the tool registry in state."""
        # Try to find the tool spec through the context/state
        state = context.state
        if state is not None:
            # Look for tool_registry on the state or executor
            registry = getattr(state, "tool_registry", None)
            if registry is None:
                # Check executor which might be on the state
                executor = getattr(state, "executor", None)
                if executor is not None:
                    registry = getattr(executor, "tool_registry", None)
            if registry is not None and hasattr(registry, "get"):
                tool = registry.get(tool_name)
                if tool is not None and hasattr(tool, "spec"):
                    return getattr(tool.spec, "read_only", False)
        return False

    def before_execute(self, action: Action, context: InterceptorContext) -> Action:
        """Return action unchanged; cache lookup happens conceptually here.

        We mark the action with metadata so that ``after_execute`` knows
        whether the tool is read-only for caching purposes.
        """
        is_ro = self._is_read_only(action.name, context)
        new_meta = dict(action.metadata)
        new_meta["_cache_read_only"] = is_ro

        # If we have a cache hit, mark it so after_execute can short-circuit
        key = self._cache_key(action.name, action.args)
        if is_ro and key in self._cache:
            new_meta["_cache_hit"] = True
        else:
            new_meta["_cache_hit"] = False

        return Action(
            name=action.name,
            args=dict(action.args),
            kind=action.kind,
            action_id=action.action_id,
            timeout_s=action.timeout_s,
            max_retries=action.max_retries,
            idempotent=action.idempotent,
            classification=action.classification,
            metadata=new_meta,
        )

    def after_execute(
        self, action: Action, result: ActionResult, context: InterceptorContext
    ) -> ActionResult:
        """Cache the result if the tool is read-only and the call succeeded."""
        is_ro = action.metadata.get("_cache_read_only", False)
        cache_hit = action.metadata.get("_cache_hit", False)

        if not is_ro:
            return result

        key = self._cache_key(action.name, action.args)

        if cache_hit and key in self._cache:
            # Return the cached result and update access order
            self._touch(key)
            return self._cache[key]

        # Store successful results in the cache
        if result.status == ActionStatus.SUCCESS:
            if key in self._cache:
                self._touch(key)
                self._cache[key] = result
            else:
                self._cache[key] = result
                self._insertion_order.append(key)
            # Evict least-recently-used entries if over max_size
            while len(self._cache) > self.max_size:
                lru_key = self._insertion_order.pop(0)
                self._cache.pop(lru_key, None)

        return result

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._insertion_order.clear()


__all__ = ["CacheInterceptor"]
