"""Run one explicit stage; importing this entry point has no side effects."""

import sys
from pathlib import Path


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from method_a_final_evaluation.cli import main

    main()
