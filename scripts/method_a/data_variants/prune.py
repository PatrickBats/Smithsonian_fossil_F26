"""Remove only this suite's own redundant checkpoints after successful validation."""

import argparse, os
from common import EXPERIMENTS, RESULTS, ROOT, load, resolve_variant, sha, write

p = argparse.ArgumentParser()
p.add_argument(
    "--variant",
    "--experiment",
    dest="experiment",
    type=resolve_variant,
    choices=EXPERIMENTS,
    required=True,
    metavar="A1|A2|A3",
)
a = p.parse_args()
run = ROOT / "run_artifacts" / a.experiment
validation = RESULTS / a.experiment / "validation"
assert load(run / "training/status.json")["status"] == "completed"
assert load(validation / "status.json")["status"] == "completed"
checkpoint = run / "training/checkpoint_final_ema.pth"
expected = load(run / "training/status.json")["checkpoint_sha256"]
assert sha(checkpoint) == expected == load(validation / "summary.json")["checkpoint_sha256"]
removed = []
for directory in (run / "smoke", run / "training"):
    for path in sorted(directory.iterdir()):
        if path.suffix not in (".pth", ".ckpt") or path == checkpoint:
            continue
        st = path.lstat()
        assert (
            st.st_uid == os.getuid()
            and st.st_nlink == 1
            and path.is_file()
            and not path.is_symlink()
        )
        removed.append({"path": str(path), "bytes": st.st_size, "sha256": sha(path)})
        path.unlink()
assert sha(checkpoint) == expected
write(
    run / "checkpoint_pruning.json",
    {
        "status": "completed",
        "retained": str(checkpoint),
        "retained_sha256": expected,
        "removed": removed,
        "bytes_reclaimed": sum(r["bytes"] for r in removed),
    },
)
