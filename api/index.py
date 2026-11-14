import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "backend"), ROOT):  # package may live in backend/ or directly in the repo root
    if p not in sys.path:
        sys.path.insert(0, p)

from novaapi.entry import app  # noqa: E402,F401
