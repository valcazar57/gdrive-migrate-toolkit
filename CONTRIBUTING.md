# Contributing

> Maintainer's note: this is my first open-source project. Reviews, fixes and
> suggestions are very welcome — be kind, be specific, and never include real data.

Thanks for considering a contribution. This project is small and dependency-free
on purpose — keep it that way.

## Ground rules

- **No real data, ever.** No account names, brands, clients, emails, Drive IDs,
  share-URLs or `rclone.conf`. See [SECURITY.md](SECURITY.md). PRs containing real
  identifiers will be closed.
- **Standard library only** for the Python scripts (no `pip install` for users).
- **Dry-run by default** must hold for any new script or flag. Destructive actions
  require an explicit `--apply`.
- **Cross-platform**: scripts should work on Windows + Git Bash, macOS and Linux.
  Pass rclone args as a list (no shell), redirect large listings to a file.

## How to contribute

1. Open an issue describing the problem or improvement first.
2. Keep changes focused; update the relevant `docs/` page if behavior changes.
3. Test against **your own empty test remotes/folders**, never someone else's data.
   Include the exact commands you ran (with placeholders) in the PR.
4. New gotchas are very welcome — add them to [docs/GOTCHAS.md](docs/GOTCHAS.md) with
   a one-line "what it cost / how to avoid".

## Style

- Code comments and docs in **English** (this is the international repo language).
- Keep the method aligned with [PLAYBOOK.md](PLAYBOOK.md); if you change the method,
  update the PLAYBOOK and the affected `docs/`.

## Manual pre-release verification (maintainers)

The automated tests are **offline** (a fake rclone): they cover command
construction, logging, error handling and exit codes — not real Drive behavior.
Before tagging a release, run a manual smoke against **two throwaway test accounts**
(never real data) covering: a real Google Doc/Sheet (native preserved server-side),
a shortcut, duplicate names, a non-owned file (404 on pass 1, recovered via pass 2),
and a `verify_counts.py --check` pass.

## Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).
