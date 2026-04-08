from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)

# Keep the repository root at the front so tests import this checkout's
# `examples` package instead of relying on namespace-package resolution.
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)
