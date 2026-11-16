"""Command entry point for method_a_new_delivery.crop_plan."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from method_a_new_delivery.crop_plan import main

if __name__ == "__main__":
    main()
