"""Entry: python -m skill_retriever"""
import sys
from pathlib import Path

_src = Path(__file__).parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from skill_retriever.cli import main

if __name__ == "__main__":
    sys.exit(main())
