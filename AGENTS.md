# Working repository rules

Repository: `PatrickBats/Smithsonian_fossil_F26`.

- Keep assistant changes local unless the user explicitly requests a push. Authorization for the initial copy/setup does not authorize future routine pushes.
- Never push or merge changes into `RiceD2KLab/Smithsonian_fossil_F26` without separate explicit direction.
- Use feature branches and pull requests for shared changes. Patrick reviews collaborator changes before merging into `main`; do not merge automatically.
- Run the repository checks and relevant tests before proposing changes. Passing the current documentation/source checks does not establish model or application correctness.
- Keep credentials, raw NDPI images, model weights, and experiment outputs out of Git. Preserve original source documents and their manifest hashes.
- Follow the applicable workspace compute policy. Scientific protocol decisions must remain explicit; do not infer authorization to launch training from a documentation task.

- Read `docs/CURRENT_CONTEXT.md`. Use the verified Fall_2026 source annotations in `docs/sources/data/Fall_2026/` and inventories in `data/current/` for new work. All 185 title counts reconcile with sponsor tables; old provisional aliases are superseded. `data/current/classification_annotations.csv` has 2,290 YES records under the supplied categories, not a finalized broad-category or sampled training set. Keep `data/archive/` historical. Preserve source names and versions, and use `data/current/cluster_source_paths.csv` for the verified NOTS annotation/image paths; the annotations_F26 directory alone contains only 48 of 83 files.
