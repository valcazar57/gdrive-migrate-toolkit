# gdrive-migrate-toolkit

**Reorganize, deduplicate, migrate, evacuate and merge Google Drive / Google Workspace
accounts at scale with [rclone](https://rclone.org/) — without losing data, and
reversibly.**

![CI](https://github.com/valcazar57/gdrive-migrate-toolkit/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)

There is no official tool to **reorganize / merge / evacuate / deduplicate a
company Google Drive at scale**: multiple accounts, Drive-for-Desktop virtual
files that hang `find`, Google-native files that aren't real bytes, API
throttling, Windows path limits. This toolkit is the method + scripts that solve
it, distilled from doing it for real on a multi-account Workspace with tens of GB.

It is built on one safety contract: **copy → verify → delete-to-trash**, never a
bare move out of the cloud. Every script is **dry-run by default**.

Run the scripts yourself, or let **any** AI coding agent drive them — the operating
rules live in [AGENTS.md](AGENTS.md), a tool-agnostic convention (not tied to any
single assistant).

## The problem this solves

- A company Drive grew into a dumping ground across **several accounts**.
- `find`/`du` over the mounted Drive letter **hangs** (Drive for Desktop hydrates
  every placeholder from the cloud).
- **Google-native** Docs/Sheets/Slides are cloud-only pointers — naive backups lose
  them silently.
- Copying **between accounts** 404s on everything you don't own.
- rclone **throttles** (HTTP 429) the moment you run two jobs on one account.
- No official "merge these Drives / empty this account into those" button exists.

## What it does

| Capability | Script | Doc |
|---|---|---|
| Inventory without hanging Drive | `detect_natives.py` | [docs/02](docs/02-inventory.md) |
| Local mirror (safety net; exports natives) | `mirror_account.py` | [docs/03](docs/03-local-mirror.md) |
| Reorganize **in-place** (server-side move, preserves natives) | `reorg_move.py` | [docs/04](docs/04-reorg-intra-account.md) |
| **Evacuate** an account across others + disk (2 passes) | `evacuate.py` | [docs/05](docs/05-evacuation-cross-account.md) |
| Deduplicate & quarantine | — (recipes) | [docs/06](docs/06-dedup-and-quarantine.md) |
| Verify (count/hash) & delete reversibly | `verify_counts.py` | [docs/07](docs/07-verify-and-delete.md) |
| Upload disk → Drive (and back) | — (recipes) | [docs/08](docs/08-disk-to-drive.md) |
| Plan space & distribution | — (recipes) | [docs/10](docs/10-space-and-distribution.md) |

The full method is in [**PLAYBOOK.md**](PLAYBOOK.md). Every hard-won trap is in
[**docs/GOTCHAS.md**](docs/GOTCHAS.md).

## Why not an existing tool?

The engine here is **rclone** — the one piece that can copy/move *between accounts*
while preserving Google-native files (`--drive-server-side-across-configs`) and
reparent server-side *within* an account (`rclone move`). Almost no other Drive
client does that. GAM helps only for ownership transfer **within a single Workspace
domain**; everything else (single-account clients, FUSE mounts, public-link
downloaders) can't do safe, native-preserving, cross-account reorganization. The
value of this repo is the **method** on top of rclone. Full comparison in
[docs/11-prior-art.md](docs/11-prior-art.md).

## Quickstart

```bash
# 0. Install rclone, then create one remote per Google account (2+ letter names!)
rclone config create accountA drive scope=drive
rclone about accountA:          # sanity check: small cloud quota = OK

# 1. Mirror the account to disk (your real safety net) — dry-run, then --apply
python scripts/mirror_account.py --remote accountA: --dest D:/MIRROR
python scripts/mirror_account.py --remote accountA: --dest D:/MIRROR --apply

# 2. Reorganize in place with a CSV of moves (dry-run by default)
cp templates/move_table.example.csv move_table.csv   # edit it: group;source;dest;mirror
python scripts/reorg_move.py --table move_table.csv --src-remote accountA: --dst-remote accountA:
python scripts/reorg_move.py --table move_table.csv --src-remote accountA: --dst-remote accountA: --apply

# 3. Or evacuate an account across others + disk (2 passes)
python scripts/evacuate.py --table move_table.csv --src-remote accountA: --dst-remote accountB: --pass 1 --apply  # owned, server-side
python scripts/evacuate.py --table move_table.csv --src-remote accountA: --dst-remote accountB: --pass 2 --apply  # non-owned, relay from mirror

# 4. Verify, then delete the source to trash (reversible 30 days)
python scripts/verify_counts.py --table move_table.csv --src-remote accountA: --dst-remote accountB:
rclone purge "accountA:SomeBlock" --drive-use-trash=true
```

Requirements: **Python 3.8+** (standard library only) and **rclone**. No `pip
install` needed. Tested on **Windows + Google Drive for Desktop**; the method
applies to macOS/Linux too — PRs for those environments are welcome.

## Critical warnings

- **Copy, never move *from* Drive.** A bare move out of a synced folder deletes the
  cloud copy. This toolkit always copies, verifies, then deletes to trash.
- **Google-native survive as natives only inside Drive.** Going to disk exports them
  to Office. See [docs/08](docs/08-disk-to-drive.md).
- **The 30-day trash is a net, not a backup.** Your verified local mirror is the
  backup.
- **One rclone per account** — two at once = HTTP 429.
- **Don't move live editing projects** (`.prproj`/`.drp` link media by path).

## Repository layout

```
README.md                  The story + quickstart
PLAYBOOK.md                The full method (anonymized)
AGENTS.md                  Operating rules for any AI/automation agent
LICENSE                    MIT
SECURITY.md                Never commit rclone.conf; how to report
docs/                      00-principles ... 11-prior-art + GOTCHAS
scripts/                   reorg_move, mirror_account, evacuate, verify_counts, detect_natives, common
templates/                 move_table.example.csv, changes.schema.csv
tests/                     offline smoke test (fake rclone, no network)
.github/                   CI workflow + PR template
```

## Safety & privacy

This repo contains **method + generic scripts + empty templates only**. No
credentials, no real data, no account/brand/client names. Never commit your
`rclone.conf`, logs or change CSVs — see [SECURITY.md](SECURITY.md) and
[.gitignore](.gitignore).

## Author

Built by **Victor Alcazar** — <https://victoralcazar.com>.

## Contributing & feedback

This is my **first open-source project**, born from solving a real multi-account
Google Drive cleanup. If something is unclear, broken, or could be done better,
your feedback is genuinely welcome — open an issue or a PR. New traps for
[`docs/GOTCHAS.md`](docs/GOTCHAS.md) are especially appreciated. See
[CONTRIBUTING.md](CONTRIBUTING.md) and, before anything else, [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE). Use at your own risk; you are responsible for your own data —
always dry-run, mirror, and verify before deleting anything.
