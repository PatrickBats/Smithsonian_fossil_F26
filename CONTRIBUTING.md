# Working together

This public repository is an independent copy of the class project's documentation branch at commit `8949b1553e4dcd822a392240795ac7abbe76fdea`. It preserves the 24 original tracked files and their history. Its Git remote points to Patrick's working repository, not the RiceD2KLab repository. Large project data remains on NOTS.

## Access and review

Patrick owns this repository. He can invite collaborators through repository **Settings → Collaborators**. At the user’s explicit request, invitations were sent to `baoyunfan0101`, `alanyangrice`, `tsaiyunying`, and `yk86-commits`. Each invitee must accept their invitation before collaborating with write access.

1. Create a feature branch from current `main`.
2. Make a focused change and run `python scripts/check_repository.py`, plus tests relevant to the change.
3. Push the feature branch and open a pull request against this repository's `main`.
4. Explain the change and validation in the PR. Patrick reviews it before merging.

The CODEOWNERS file names `@PatrickBats` for all files. Protection is enabled on `main`: collaborator changes require a pull request, one approval from the code owner, a successful up-to-date `Repository checks` status, and resolved review conversations. New changes dismiss prior approvals. Force pushes and branch deletion are disabled; squash merging is enabled and automatic merging is disabled.

Patrick retains owner/admin control and can bypass the review rule for his own changes. Collaborators cannot use that owner privilege. The repository is public by the user's choice; code and documentation are publicly readable, while raw data remains on NOTS. Protection was enabled after changing visibility because the account could not enable it for a private repository. See [GitHub's protected-branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

For AI-assisted work in this task, the user explicitly requires permission before future pushes. Initial repository creation/upload does not authorize ongoing automatic pushes or merges. The class repository is a separate destination and must not receive changes without explicit direction.

## What automated checks cover

The `Repository checks` workflow verifies source-file hashes and sizes against the manifest, internal Markdown file links, Python syntax, and whitespace in the proposed change. It runs on pushes to `main`, pull requests, and manual dispatch.

These checks protect the current documentation/source repository; they cannot guarantee future software or model correctness. Add behavior tests, data-validation checks, and experiment validation as implementation arrives. Patrick's review remains necessary.

Original source material is retained as evidence. When intentionally adding or revising source records, update provenance and checksums explicitly. Do not put raw microscope slides, credentials, large model checkpoints, or experiment outputs into Git.
