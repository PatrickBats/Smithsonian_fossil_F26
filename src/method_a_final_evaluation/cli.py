"""Command parsing for the mixed-delivery final evaluation workflow."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--old-manifest", required=True)
    prepare.add_argument("--new-plan-root", required=True)
    prepare.add_argument("--maps", required=True)
    prepare.add_argument("--root", required=True)
    prepare.add_argument("--seed", type=int, default=20261120)
    export = sub.add_parser("export")
    export.add_argument("--root", required=True)
    export.add_argument("--index", type=int, required=True)
    export.add_argument("--limit", type=int)
    for name in ("assemble", "ignore", "train", "predict"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        p.add_argument("--stage", choices=("cv", "final"), required=True)
        p.add_argument("--fold", type=int)
        if name != "assemble":
            p.add_argument("--run-root", required=True)
        if name == "train":
            p.add_argument("--kind", choices=("teacher", "model"), required=True)
            p.add_argument("--generic-init", required=True)
            p.add_argument("--generic-sha", required=True)
            p.add_argument("--steps", type=int, default=2400)
            p.add_argument("--smoke", action="store_true")
        if name in ("train", "predict"):
            p.add_argument("--results", required=True)
    for name in ("select", "report"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        p.add_argument("--run-root", required=True)
        p.add_argument("--results", required=True)
    a = vars(parser.parse_args())
    command = a.pop("command")
    if command in ("prepare", "export"):
        from . import preparation

        result = getattr(preparation, command)(**a)
    elif command in ("assemble", "ignore"):
        from . import datasets

        result = (datasets.assemble if command == "assemble" else datasets.add_ignore)(
            **a
        )
    elif command == "train":
        from .training import train

        result = train(**a)
    else:
        from . import evaluation

        result = getattr(evaluation, command)(**a)
    print(json.dumps(result, indent=2), flush=True)
