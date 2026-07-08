"""Allow running as: python -m skill_retriever

Usage:
    python -m skill_retriever search "query"
    python -m skill_retriever build
    python -m skill_retriever list
    python -m skill_retriever info
"""

import sys
from pathlib import Path

# Ensure src/ is importable
_src = Path(__file__).parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from skill_retriever.cli import main

if __name__ == "__main__":
    sys.exit(main())
