"""Small Slurm controller; all image/GPU work stays in allocated jobs."""

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path

from .protocol import read


class Controller:
    def __init__(self, work, root, run_root, code, prepare_job):
        self.work, self.root, self.run_root, self.code = map(
            Path, (work, root, run_root, code)
        )
        self.results = self.work / "results"
        self.path = self.work / "jobs.json"
        self.state = (
            read(self.path)
            if self.path.exists()
            else {
                "jobs": {"prepare": {"id": str(prepare_job), "attempts": 1}},
                "events": [],
            }
        )
        self.base = ["--root", str(self.root)]
        self.run = ["--run-root", str(self.run_root)]
        self.result_args = ["--results", str(self.results)]
        self.generic = [
            "--generic-init",
            "/rhf/allocations/dsci435/Smithsonian_F26/weights/rf-detr-xxlarge.pth",
            "--generic-sha",
            "bf418652d5e07ad441599acfadc65bb1767029079e7a343a6d61675ec5d553ae",
        ]

    def event(self, message):
        record = {
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": message,
        }
        self.state["events"].append(record)
        print(json.dumps(record), flush=True)
        self.save()

    def save(self):
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.state, indent=2) + "\n")
        temp.replace(self.path)

    def submit(self, name, args, gpu=False, short=False, array=None):
        previous = self.state["jobs"].get(name)
        if previous and previous.get("attempts", 0) >= 8:
            raise RuntimeError(f"Too many attempts: {name}")
        script = (
            self.code
            / "scripts"
            / "method_a_final_evaluation"
            / ("gpu.sbatch" if gpu else "cpu.sbatch")
        )
        command = [
            "sbatch",
            "--parsable",
            "--job-name=" + name[:24],
            "--output=" + str(self.work / "logs" / (name + "-%j.out")),
            "--error=" + str(self.work / "logs" / (name + "-%j.err")),
            "--export=ALL,MIXED_CODE_ROOT="
            + str(self.code)
            + ",MIXED_CHUNK_MINUTES=44",
        ]
        if gpu and not short:
            command += [
                "--partition=scavenge",
                "--qos=nots_scavenge",
                "--time=00:55:00",
            ]
        elif gpu:
            command += ["--partition=debug", "--qos=nots_debug", "--time=00:25:00"]
        elif array is not None:
            command += [
                "--account=commons",
                "--partition=commons",
                "--qos=nots_commons",
                "--time=01:00:00",
                "--cpus-per-task=4",
                "--mem=12G",
                "--array=" + array,
            ]
        if array is None:
            command += [str(script), *args]
        else:
            # Only this remote Slurm variable expands; all supplied paths/args
            # are shell-quoted before appending the source-index argument.
            entry = [
                "/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python",
                str(self.code / "scripts" / "method_a_final_evaluation" / "run.py"),
                *args,
            ]
            command += [
                "--wrap",
                "export PYTHONPATH="
                + shlex.quote(str(self.code / "src"))
                + "; "
                + shlex.join(entry)
                + ' --index "$SLURM_ARRAY_TASK_ID"',
            ]
        job = subprocess.check_output(command, text=True).strip().split(";")[0]
        history = (
            previous.get("history", []) + [{"id": previous["id"]}] if previous else []
        )
        self.state["jobs"][name] = {
            "id": job,
            "attempts": previous.get("attempts", 0) + 1 if previous else 1,
            "args": args,
            "gpu": gpu,
            "short": short,
            "array": array,
            "history": history,
        }
        self.event(f"Submitted {name}: {job}")

    def statuses(self):
        ids = sorted({j["id"] for j in self.state["jobs"].values()})
        raw = subprocess.check_output(
            [
                "sacct",
                "-n",
                "-X",
                "-P",
                "-j",
                ",".join(ids),
                "--format=JobID%60,State%40,ExitCode",
            ],
            text=True,
        )
        groups = {}
        for line in raw.splitlines():
            fields = line.split("|")
            if len(fields) >= 3:
                root = fields[0].split("_")[0]
                groups.setdefault(root, []).append(
                    (fields[1].split()[0].rstrip("+"), fields[2])
                )
        statuses = {}
        for name, job in self.state["jobs"].items():
            values = groups.get(job["id"], [])
            job["slurm_states"] = values
            expected = (
                int(job["array"].split("-")[1].split("%")[0]) + 1
                if job.get("array")
                else 1
            )
            if len(values) >= expected and all(
                s == "COMPLETED" and code == "0:0" for s, code in values
            ):
                state = "done"
            elif any(code != "0:0" and s == "COMPLETED" for s, code in values) or any(
                s
                in {
                    "FAILED",
                    "CANCELLED",
                    "OUT_OF_MEMORY",
                    "NODE_FAIL",
                    "PREEMPTED",
                    "TIMEOUT",
                    "BOOT_FAIL",
                }
                for s, _ in values
            ):
                state = "failed"
            else:
                state = "active"
            statuses[name] = state
            if job.get("last_state") != state:
                job["last_state"] = state
                self.event(f"{name} is {state}")
        return statuses

    def tick(self):
        states = self.statuses()
        for name, state in states.items():
            if state == "failed":
                job = self.state["jobs"][name]
                retryable = any(
                    s in {"NODE_FAIL", "PREEMPTED", "TIMEOUT", "BOOT_FAIL"}
                    for s, _ in job.get("slurm_states", [])
                )
                if retryable and name.endswith(("teacher", "model")):
                    args = job["args"]
                    tag = "final" if "final" in name else "fold_" + name.split("-")[1]
                    kind = "teacher" if name.endswith("teacher") else "model"
                    if (self.run_root / tag / kind / "resume.ckpt").exists():
                        self.submit(name, args, gpu=job["gpu"], short=job["short"])
                        return False
                raise RuntimeError(
                    f"Job failed: {name}, {job['id']}; inspect its stderr before resubmitting"
                )
        for name, state in list(states.items()):
            if state == "done" and name.endswith(("teacher", "model")):
                tag = "final" if "final" in name else "fold_" + name.split("-")[1]
                kind = "teacher" if name.endswith("teacher") else "model"
                path = self.run_root / tag / kind / "status.json"
                if path.exists() and read(path)["status"] == "paused":
                    job = self.state["jobs"][name]
                    self.submit(name, job["args"], gpu=True, short=False)
                    return False

        def ready(name):
            return states.get(name) == "done"

        def absent(name):
            return name not in states

        if ready("prepare") and absent("export"):
            count = read(self.root / "protocol.json")["scan_count"]
            self.submit("export", ["export", *self.base], array=f"0-{count - 1}%16")
        if ready("export"):
            for fold in [*range(5), None]:
                tag = "final" if fold is None else f"cv-{fold}"
                stage = (
                    ["--stage", "final"]
                    if fold is None
                    else ["--stage", "cv", "--fold", str(fold)]
                )
                if absent(tag + "-assemble"):
                    self.submit(tag + "-assemble", ["assemble", *self.base, *stage])
        if ready("cv-0-assemble") and absent("smoke-teacher"):
            self.submit(
                "smoke-teacher",
                [
                    "train",
                    *self.base,
                    *self.run,
                    *self.result_args,
                    *self.generic,
                    "--stage",
                    "cv",
                    "--fold",
                    "0",
                    "--kind",
                    "teacher",
                    "--smoke",
                ],
                gpu=True,
                short=True,
            )
        if ready("smoke-teacher") and absent("smoke-model"):
            self.submit(
                "smoke-model",
                [
                    "train",
                    *self.base,
                    *self.run,
                    *self.result_args,
                    *self.generic,
                    "--stage",
                    "cv",
                    "--fold",
                    "0",
                    "--kind",
                    "model",
                    "--smoke",
                ],
                gpu=True,
                short=True,
            )
        if ready("smoke-model"):
            for fold in [*range(5), None]:
                tag = "final" if fold is None else f"cv-{fold}"
                stage = (
                    ["--stage", "final"]
                    if fold is None
                    else ["--stage", "cv", "--fold", str(fold)]
                )
                if ready(tag + "-assemble") and absent(tag + "-teacher"):
                    self.submit(
                        tag + "-teacher",
                        [
                            "train",
                            *self.base,
                            *self.run,
                            *self.result_args,
                            *self.generic,
                            *stage,
                            "--kind",
                            "teacher",
                        ],
                        gpu=True,
                    )
                if ready(tag + "-teacher") and absent(tag + "-ignore"):
                    self.submit(
                        tag + "-ignore",
                        ["ignore", *self.base, *self.run, *stage],
                        gpu=True,
                        short=True,
                    )
                if (
                    fold is not None
                    and ready(tag + "-ignore")
                    and absent(tag + "-model")
                ):
                    self.submit(
                        tag + "-model",
                        [
                            "train",
                            *self.base,
                            *self.run,
                            *self.result_args,
                            *self.generic,
                            *stage,
                            "--kind",
                            "model",
                        ],
                        gpu=True,
                    )
                if (
                    fold is not None
                    and ready(tag + "-model")
                    and absent(tag + "-predict")
                ):
                    self.submit(
                        tag + "-predict",
                        ["predict", *self.base, *self.run, *self.result_args, *stage],
                        gpu=True,
                        short=True,
                    )
        if all(ready(f"cv-{i}-predict") for i in range(5)) and absent("select"):
            self.submit("select", ["select", *self.base, *self.run, *self.result_args])
        if ready("select") and ready("final-ignore") and absent("final-model"):
            self.submit(
                "final-model",
                [
                    "train",
                    *self.base,
                    *self.run,
                    *self.result_args,
                    *self.generic,
                    "--stage",
                    "final",
                    "--kind",
                    "model",
                ],
                gpu=True,
            )
        if ready("final-model") and absent("final-predict"):
            self.submit(
                "final-predict",
                [
                    "predict",
                    *self.base,
                    *self.run,
                    *self.result_args,
                    "--stage",
                    "final",
                ],
                gpu=True,
                short=True,
            )
        if ready("final-predict") and absent("report"):
            self.submit("report", ["report", *self.base, *self.run, *self.result_args])
        if ready("report"):
            self.event("Final mixed-delivery test assessment completed")
            return True
        self.save()
        return False


def main():
    parser = argparse.ArgumentParser()
    for name in ("work", "root", "run-root", "code", "prepare-job"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--watch", action="store_true")
    args = vars(parser.parse_args())
    watch = args.pop("watch")
    controller = Controller(**args)
    while True:
        if controller.tick() or not watch:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
