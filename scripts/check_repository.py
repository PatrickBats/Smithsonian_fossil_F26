"""Lightweight checks for this repository; no dataset or cluster access needed."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


def check(root: Path) -> list[str]:
    errors = []
    manifest = json.loads((root / "docs/sources/manifest.json").read_text())
    seen = set()
    for entry in manifest["sources"]:
        name = entry["repository_path"]
        path = (root / name).resolve()
        if not path.is_relative_to(root) or name in seen:
            errors.append(f"Invalid or duplicate source path: {name}")
            continue
        seen.add(name)
        if not path.is_file():
            errors.append(f"Missing source: {name}")
            continue
        data = path.read_bytes()
        if len(data) != entry["size_bytes"]:
            errors.append(f"Source size differs: {name}")
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            errors.append(f"Source checksum differs: {name}")

    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=root
    ).decode().split("\0")
    for name in filter(None, tracked):
        path = root / name
        if not path.is_file():
            errors.append(f"Tracked file missing: {name}")
            continue
        if path.suffix == ".py":
            try:
                compile(path.read_bytes(), name, "exec")
            except (SyntaxError, ValueError) as error:
                errors.append(f"Python syntax: {name}: {error}")
        if path.suffix != ".md":
            continue
        # Check inline file links; remote URLs and same-file anchors are excluded.
        # Remove code blocks so example Markdown is not treated as a real link.
        content = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        for target in re.findall(r"\]\(([^\n)]+)\)", content):
            target = target.strip()
            if target.startswith("<") and ">" in target:
                target = target[1:target.index(">")]
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            file_part = unquote(target.split("#", 1)[0])
            destination = (path.parent / file_part).resolve()
            if not destination.is_relative_to(root) or not destination.exists():
                errors.append(f"Broken internal file link: {name}: {target}")
    return errors


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[1]
    try:
        failures = check(repository)
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        failures = [f"Repository check could not complete: {error}"]
    if failures:
        print("\n".join(failures), file=sys.stderr)
        sys.exit(1)
    print("Source integrity, internal Markdown file links, and Python syntax passed.")
