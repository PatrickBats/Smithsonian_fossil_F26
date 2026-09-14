# Working repository rules

This is Patrick Batsell's private working copy: `PatrickBats/Smithsonian_fossil_F26`.

- Keep assistant changes local unless the user explicitly requests a push. Authorization for the initial copy/setup does not authorize future routine pushes.
- Never push or merge changes into `RiceD2KLab/Smithsonian_fossil_F26` without separate explicit direction.
- Use feature branches and pull requests for shared changes. Patrick reviews collaborator changes before merging into `main`; do not merge automatically.
- Run the repository checks and relevant tests before proposing changes. Passing the current documentation/source checks does not establish model or application correctness.
- Keep credentials, raw NDPI images, model weights, and experiment outputs out of Git. Preserve original source documents and their manifest hashes.
- Follow the applicable workspace compute policy. Scientific protocol decisions must remain explicit; do not infer authorization to launch training from a documentation task.
