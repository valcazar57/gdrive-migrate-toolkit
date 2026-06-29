# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/valcazar57/gdrive-migrate-toolkit/releases/tag/v0.1.0
