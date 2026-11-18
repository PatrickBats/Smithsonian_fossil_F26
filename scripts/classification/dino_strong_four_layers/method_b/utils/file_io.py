"""Artifact I/O and source snapshots for the recorded Method B workflows.

Separate write functions retain the original experiment's serialization policies.
"""
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

def digest(path):
    """Compute the SHA-256 fingerprint of a file.

    Args:
        path: Path to the file to read or validate.

    Returns:
        str: Lowercase hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    """Read specimen or category CSV records.

    Args:
        path: Path to the file to read or validate.

    Returns:
        list[dict]: Records in file order.
    """
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def write_json(path, obj):
    """Write a JSON artifact, rejecting nonfinite numeric values.

    Args:
        path: Path to the file to read or validate.
        obj: JSON-serializable value to write.

    Returns:
        None: Writes the supplied JSON artifact.
    """
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def rows(path):
    """Read a UTF-8 CSV manifest, accepting a byte-order mark.

    Args:
        path: Path to the file to read or validate.

    Returns:
        list[dict]: Records in file order.
    """
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def sha(path):
    """Compute the SHA-256 fingerprint of a file.

    Args:
        path: Path to the file to read or validate.

    Returns:
        str: Lowercase hexadecimal SHA-256 digest.
    """
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def save(path, data):
    """Write the experiment artifact using this workflow's recorded save policy.

    Args:
        path: Path to the file to read or validate.
        data: Payload to serialize or append.

    Returns:
        None: Writes the supplied artifact to disk.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Concurrent array tasks must never share a temporary filename.
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        # mkstemp defaults to 0600; team-owned outputs must remain group-readable.
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, allow_nan=False) + "\n")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def sha256(path):
    """Return a file's SHA-256 using bounded memory."""
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path, expected):
    """Raise if the supplied file differs from its published fingerprint."""
    if sha256(path) != expected:
        raise ValueError(f"Checkpoint checksum mismatch: {path}")


def source_file(name):
    """Locate a renamed helper for the original per-run provenance snapshots.

    Args:
        name: Historical helper basename used in the recorded run directory.

    Returns:
        pathlib.Path: Current source module corresponding to that helper.
    """
    package = Path(__file__).resolve().parents[1]
    paths = {
        "train_swin.py": "classification/train_swin.py",
        "train_dino_finetune.py": "classification/train_dinov2.py",
        "specimen_split.py": "preprocessing/data_splits.py",
        "broad_labels.py": "preprocessing/category_mapping.py",
    }
    return package / paths[name]


def snapshot_package(output):
    """Preserve the package dependencies beside a new training run's snapshots.

    Args:
        output: Existing training-run output directory.

    Returns:
        None: Writes a source/method_b tree of Python files; changed files are rejected.
    """
    package = Path(__file__).resolve().parents[1]
    destination = Path(output) / "source" / "method_b"
    for source in sorted(package.rglob("*.py")):
        if any(part in ("__pycache__", "tests") for part in source.relative_to(package).parts):
            continue
        target = destination / source.relative_to(package)
        payload = source.read_bytes()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != payload:
            raise ValueError(f"Run source snapshot changed: {target}")
        if not target.exists():
            target.write_bytes(payload)
