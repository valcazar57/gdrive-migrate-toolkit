# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-29

Safer-by-default for automation (second external review).

### Changed
- **Cross-account `move` is now BLOCKED by default** in `reorg_move.py`; it requires
  the explicit `--allow-cross-account-move`. Use `evacuate.py` (copy -> verify ->
  delete) for cross-account transfers.
- Scripts return meaningful **exit codes**: `reorg_move.py` / `evacuate.py` exit `1`
  on hard failures, `2` when a row needs REVIEW, `0` only when clean — so a `0` exit
  can gate automation. A REVIEW (e.g. added != source) is no longer silent success.

### Added
- `verify_counts.py --check` runs `rclone check --one-way` (paths + sizes/hashes)
  for strong verification, and reports access errors as `source_error`/`dest_error`.
- `evacuate.py` surfaces destinations it could not measure as
  `REVIEW(dest_unmeasured)` instead of `ok`, and tracks a global failure/review count.

### Fixed
- Timeouts during measurement (`rclone size`/`lsf`) and during `evacuate` copies are
  now converted to clean errors instead of an uncaught exception.

### Docs
- Documented the `--ignore-existing` trade-off in pass 2 (skips by name, not
  content), a manual pre-release verification checklist, and the supervised scope.

## [0.1.1] - 2026-06-29

Robustness and accuracy pass (from external review feedback).

### Changed
- Use the modern global `--server-side-across-configs` flag (the Drive-specific
  `--drive-server-side-across-configs` is deprecated upstream).
- Clarified that Google-native files stay native **only on server-side transfers**;
  files recovered via the local-mirror relay (non-owned, evacuate pass 2) are
  restored as Office exports.

### Fixed
- `common.rclone_size` / `rclone_count_files` now distinguish "path not found"
  (returns `None`) from a real failure (raises `RcloneError`), so `reorg_move.py`
  no longer mistakes a timeout / 429 / auth error for an already-moved source and
  silently skips it; it also exits non-zero when any row fails.
- `reorg_move.py` logs the true number of objects **added** to the destination
  (`dest_after - dest_before`) instead of the destination total, and flags a
  mismatch with the source count.
- `verify_counts.py` reports access errors as `source_error` / `dest_error`
  (exit non-zero) instead of treating them like an empty path.
- `reorg_move.py` warns that cross-account `move` copies-then-deletes per file and
  points to `evacuate.py` for the safer copy → verify → delete path.

### Added
- Offline error-path tests (missing vs unreadable source, verify errors) and
  Windows runners in CI (Ubuntu + Windows, Python 3.8 and 3.12).

## [0.1.0] - 2026-06-29

First public release.

### Added
- Method (`PLAYBOOK.md`) and step-by-step docs (`docs/00`–`docs/11`, including a
  prior-art comparison), plus hard-won traps in `docs/GOTCHAS.md`.
- Scripts (standard-library only, dry-run by default): `detect_natives.py`,
  `mirror_account.py`, `reorg_move.py`, `evacuate.py`, `verify_counts.py`, and
  shared `common.py`.
- Templates: `templates/move_table.example.csv`, `templates/changes.schema.csv`.
- Offline smoke tests (`tests/`) with a fake rclone, and GitHub Actions CI
  (Python 3.8 and 3.12).
- Project docs and community files: `README.md`, `AGENTS.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, `CODE_OF_CONDUCT.md`, `LICENSE` (MIT), PR and issue templates.

[0.2.0]: https://github.com/valcazar57/gdrive-migrate-toolkit/releases/tag/v0.2.0
[0.1.1]: https://github.com/valcazar57/gdrive-migrate-toolkit/releases/tag/v0.1.1
[0.1.0]: https://github.com/valcazar57/gdrive-migrate-toolkit/releases/tag/v0.1.0
