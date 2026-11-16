"""Output helpers used by the retained A3 focal-crop exporter."""

import hashlib
import json
import os
from pathlib import Path

from .paths import TRAINING as ROOT


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert path.is_relative_to(ROOT)
    if path.exists():
        assert path.lstat().st_uid == os.getuid() and not path.is_symlink()
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
    temporary.replace(path)


def load(path):
    return json.loads(Path(path).read_text())
