"""Command entry point for the held-out confusion figure."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from method_a_new_delivery.plot_confusion import main

if __name__ == "__main__":
    main()
