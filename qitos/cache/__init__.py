"""QitOS LLM Response Cache.

.. deprecated::
    ``qitos.cache`` is deprecated and will be removed in a future release.
    LLM response caching will move to a different module.
"""

import warnings

warnings.warn(
    "qitos.cache is deprecated and will be removed in a future release. "
    "LLM response caching will move to a different module.",
    DeprecationWarning,
    stacklevel=2,
)

from .backends import CacheBackend, DiskCache, InMemoryCache
from .wrapper import CachedModel

__all__ = ["CacheBackend", "InMemoryCache", "DiskCache", "CachedModel"]
