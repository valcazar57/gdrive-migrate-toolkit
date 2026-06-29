# 01 — Install & configure rclone

[rclone](https://rclone.org/) is the engine. It talks to the Google Drive API
directly, so it avoids the "hydration hang" you get when you point `find`/`du` at
a mounted Drive letter.

## Install

- **Windows**: download `rclone.exe` from <https://rclone.org/downloads/> and put
  it somewhere on `PATH` (e.g. `D:/_tools/rclone/rclone.exe`). Or `winget install Rclone.Rclone`.
- **macOS**: `brew install rclone`
- **Linux**: `curl https://rclone.org/install.sh | sudo bash`

The scripts find rclone via `--rclone PATH`, the `$RCLONE` env var, or `PATH`.

## Create one remote per Google account (OAuth)

```bash
rclone config create accountA drive scope=drive
```

This opens a browser for OAuth — **log in with the correct Google account**.
Repeat for each account (`accountB`, `accountC`, ...).

`scope=drive` (full access) is needed for server-side copy and purge-to-trash.
Use `scope=drive.readonly` if you only intend to inventory/mirror.

### GOTCHA: never name a remote with a single letter on Windows

A one-letter remote (`j:`) is **eclipsed by the Windows drive letter** `J:`. Use
names of **2+ letters** (`accountA`, `sales`, `content`, ...).

## Sanity check every remote

```bash
rclone about accountA:
```

- Small/realistic cloud quota (e.g. `Total: 30 GiB, Used: 18 GiB`) → the remote
  correctly points at the cloud. ✅
- ~hundreds of GiB / TiB that match your local disk → you're accidentally reading
  the local disk, not the cloud. ❌ Fix the remote.

```bash
rclone listremotes          # list configured remotes
rclone lsf --dirs-only accountA:   # top-level folders (one level, won't hang)
```

## Where the config (and your secrets) live

```bash
rclone config file          # prints the path to rclone.conf
```

`rclone.conf` contains **OAuth tokens**. It is the single most sensitive file in
this workflow. **Never commit it.** It is in `.gitignore`; see
[`../SECURITY.md`](../SECURITY.md).

## Standard flags used by the scripts

```
--transfers 8 --tpslimit 10 --drive-pacer-min-sleep 10ms --exclude desktop.ini
```

Conservative against Drive's rate limit. Raise `--transfers`/`--tpslimit` only if
you don't hit HTTP 429s. Next: [`02-inventory.md`](02-inventory.md).
