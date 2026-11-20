# Final evaluation implementation

- `protocol.py`: deterministic scan-group partitions, guarded CV selection, and
  joint detection/classification counts.
- `preparation.py`: both source inventories, identity safeguards, context plans,
  and verified focal crop export.
- `datasets.py`: fold-scoped COCO datasets and training-only ignore proposals.
- `training.py`: new proposal/joint models, EMA candidates, resumable jobs, and
  complete training contracts.
- `evaluation.py`: held-out CV inference, sealed selection, final test inference,
  and aggregate publication/provenance files.
- `figures.py`: confusion matrix PNG/PDF and per-class counts from final test
  aggregate counts, with unchanged scientific category identifiers in CSV.
- `orchestration.py`: light Slurm status monitoring and dependent-stage dispatch.
- `bundle.py`: independent training chunks in exclusive Slurm GPU steps.
- `cli.py`: argument parsing and explicit stage dispatch.

See the [workflow and NOTS paths](../../scripts/method_a_final_evaluation/README.md).
Source records, scans, and checkpoints remain outside Git. Run the thin script
under `scripts/method_a_final_evaluation/` to launch a stage; importing modules
does not access project data or start work.
