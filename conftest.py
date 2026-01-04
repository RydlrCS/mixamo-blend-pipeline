"""Pytest configuration."""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path.parent) not in sys.path:
    sys.path.insert(0, str(src_path.parent))
