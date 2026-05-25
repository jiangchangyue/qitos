"""Per-field state version tracking for checkpoints.

Borrowed from LangGraph's channel versioning:
- references/langgraph/libs/langgraph/langgraph/pregel/_loop.py
- Each state field maintains a monotonic version number.
- After ``reduce()``, Engine diffs ``state.to_dict()`` before/after and
  bumps versions for modified fields.
"""

from __future__ import annotations

import copy
from typing import Dict, Iterable

from .store import StateVersions


class StateVersionTracker:
    """Tracks per-field monotonic version numbers for a single Engine run.

    Usage::

        tracker = StateVersionTracker()
        tracker.bump("findings")        # findings -> v1
        tracker.bump_all(["x", "y"])    # x -> v1, y -> v1
        tracker.bump("findings")        # findings -> v2
        tracker.snapshot()              # {"findings": 2, "x": 1, "y": 1}
    """

    def __init__(self, initial: StateVersions | None = None) -> None:
        self._versions: StateVersions = dict(initial) if initial else {}

    # ---- mutation ----

    def bump(self, field_name: str) -> int:
        """Increment version for *field_name*, return the new version."""
        new_ver = self._versions.get(field_name, 0) + 1
        self._versions[field_name] = new_ver
        return new_ver

    def bump_all(self, modified_fields: Iterable[str]) -> StateVersions:
        """Batch-bump multiple fields.  Returns the *new* versions only."""
        new_versions: StateVersions = {}
        for f in modified_fields:
            new_versions[f] = self.bump(f)
        return new_versions

    def bump_from_diff(
        self,
        before: Dict[str, object],
        after: Dict[str, object],
    ) -> StateVersions:
        """Diff two state dicts and bump modified fields.

        Returns the new versions for fields that changed.
        """
        modified = [
            k for k in after if k not in before or after[k] != before[k]
        ]
        # also catch deleted fields (shouldn't happen but be safe)
        modified.extend(k for k in before if k not in after)
        return self.bump_all(modified)

    # ---- read ----

    def snapshot(self) -> StateVersions:
        """Return a copy of current versions."""
        return dict(self._versions)

    def get(self, field_name: str) -> int:
        """Return the current version for a field (0 if never bumped)."""
        return self._versions.get(field_name, 0)

    # ---- restore ----

    def apply_versions(self, versions: StateVersions) -> None:
        """Restore tracker state from a saved snapshot."""
        self._versions = dict(versions)


__all__ = ["StateVersionTracker"]
