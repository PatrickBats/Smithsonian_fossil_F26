"""Check submission-time Git revisions and file hashes without requiring Git on compute nodes."""
import hashlib
import json
from pathlib import Path
root = Path(__file__).resolve().parent
metadata = json.loads((root / 'source_versions.json').read_text())
assert metadata['dino_commit'] == '7764ea0f912e53c92e82eb78a2a1631e92725fc8'
for relative, expected in metadata['files'].items():
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative
print('Source revisions and file hashes verified', flush=True)
