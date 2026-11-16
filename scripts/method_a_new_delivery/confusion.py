"""Command entry point for the complete held-out confusion counts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from method_a_new_delivery.confusion import main

if __name__ == "__main__":
    main()
