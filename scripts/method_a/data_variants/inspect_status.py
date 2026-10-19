"""Read-only compact status; safe on a NOTS login node, no GPU or large-file reads."""

import getpass
import subprocess
import json
from common import EXPERIMENTS, RESULTS, ROOT, load

rows = []
for name in EXPERIMENTS:
    row = {"experiment": name}
    for stage, path in [
        ("dataset", ROOT / "datasets" / name / "dataset_summary.json"),
        ("smoke", ROOT / "run_artifacts" / name / "smoke/status.json"),
        ("training", ROOT / "run_artifacts" / name / "training/status.json"),
        ("validation", RESULTS / name / "validation/status.json"),
    ]:
        if path.is_file():
            data = load(path)
            row[stage] = data.get("status")
            if stage == "dataset":
                row["train_images"] = data["train_images"]
        else:
            row[stage] = "pending"
    progress = ROOT / "run_artifacts" / name / "training/progress.json"
    if progress.is_file():
        row["progress"] = load(progress)
    rows.append(row)
print(
    json.dumps(
        {
            "experiments": rows,
            "exported_slide_status_files": len(list((ROOT / "export_status").glob("*.json"))),
            "comparison_ready": (RESULTS / "comparison.json").is_file(),
        },
        indent=2,
    )
)
subprocess.run(
    ["squeue", "-u", getpass.getuser(), "-o", "%.18i %.10P %.20j %.2t %.10M %R"], check=True
)

subprocess.run(
    [
        "sacct",
        "-j",
        "2255055,2255093,2255094,2255098,2269057,2269058,2269059",
        "-X",
        "--format=JobID,JobName,State,ExitCode,Elapsed",
        "-P",
    ],
    check=True,
)
