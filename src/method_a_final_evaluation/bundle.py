"""Run independent training chunks in separately allocated Slurm GPU steps."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def run_bundle(manifest):
    """Use one allocation without sharing GPUs or model state between fits."""
    jobs = json.loads(Path(manifest).read_text())
    code = Path(os.environ["MIXED_CODE_ROOT"])
    logs = Path(os.environ["MIXED_BUNDLE_LOGS"])
    job_id = os.environ["SLURM_JOB_ID"]
    logs.mkdir(parents=True, exist_ok=True)

    def run(job):
        command = [
            "srun",
            "--exclusive",
            "--exact",
            "--nodes=1",
            "--ntasks=1",
            "--cpus-per-task=4",
            "--gres=gpu:lovelace:1",
            "--mem=32G",
            sys.executable,
            str(code / "scripts" / "method_a_final_evaluation" / "run.py"),
            *job["args"],
        ]
        with (logs / f"{job['name']}-{job_id}.out").open("w") as stdout:
            with (logs / f"{job['name']}-{job_id}.err").open("w") as stderr:
                return subprocess.run(command, stdout=stdout, stderr=stderr).returncode

    # Every child has one Slurm GPU step; CUDA visibility is set by Slurm.
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        codes = list(pool.map(run, jobs))
    if any(codes):
        raise RuntimeError(f"Training step exit codes: {codes}")
    return {"exit_codes": codes}
