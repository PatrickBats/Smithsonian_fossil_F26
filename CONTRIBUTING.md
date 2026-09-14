# Working together

This private repository is an independent copy of the class project's documentation branch at commit `8949b1553e4dcd822a392240795ac7abbe76fdea`. It preserves the 24 original tracked files and their history. Its Git remote points to Patrick's working repository, not the RiceD2KLab repository. Large project data remains on NOTS.

## Access and review

Patrick owns this repository. He can invite collaborators through repository **Settings → Collaborators**. No collaborators were invited automatically during setup.

1. Create a feature branch from current `main`.
2. Make a focused change and run `python scripts/check_repository.py`, plus tests relevant to the change.
3. Push the feature branch and open a pull request against this repository's `main`.
4. Explain the change and validation in the PR. Patrick reviews it before merging.

The CODEOWNERS file names `@PatrickBats` for all files. The intended `main` protection requires his code-owner approval, passing repository checks, resolved review conversations, and renewed approval after changes. Enforcement depends on the protection settings available and enabled on GitHub; a CODEOWNERS file alone does not block direct pushes. Patrick retains owner/admin control, including the ability to handle his own PRs.

For AI-assisted work in this task, the user explicitly requires permission before future pushes. Initial repository creation/upload does not authorize ongoing automatic pushes or merges. The class repository is a separate destination and must not receive changes without explicit direction.

## What automated checks cover

The `Repository checks` workflow verifies source-file hashes and sizes against the manifest, internal Markdown file links, Python syntax, and whitespace in the proposed change. It runs on pushes to `main`, pull requests, and manual dispatch.

These checks protect the current documentation/source repository; they cannot guarantee future software or model correctness. Add behavior tests, data-validation checks, and experiment validation as implementation arrives. Patrick's review remains necessary.

Original source material is retained as evidence. When intentionally adding or revising source records, update provenance and checksums explicitly. Do not put raw microscope slides, credentials, large model checkpoints, or experiment outputs into Git.
