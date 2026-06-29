# 09 — Google Drive for Desktop (streaming vs mirror)

You don't *need* Drive for Desktop for this toolkit — rclone talks to the API
directly. But many people have it installed, and it's the source of the most
confusing traps. This explains how to configure it and when NOT to trust it.

## Install

Download from <https://www.google.com/drive/download/> and sign in. You can add
**multiple accounts**; each gets its own **drive letter** on Windows (`G:`, `H:`,
`J:`, ...) or a mount point on macOS.

## Streaming vs Mirror (the key choice)

Per account, in Drive for Desktop → Preferences → "My Drive":

- **Streaming (default)**: files are **virtual placeholders** on disk; content is
  fetched (hydrated) on access. Saves disk space.
  - ⚠️ **Trap**: recursive `find`/`du`/`dir /s` over the mounted letter **hangs**,
    because it hydrates every placeholder from the cloud. Bulk `rm -rf` stalls and
    leaves phantom `desktop.ini` shells.
- **Mirror**: everything is downloaded and kept locally. Uses full disk space, but
  all files are real and fast — no hydration surprises.

For tidying work, prefer **rclone** over walking the mounted letter either way. If
you must use the mounted letter, **Mirror** mode avoids the hydration hang.

## Forcing hydration (streaming mode)

Right-click a folder → "Offline access" / "Available offline" to pre-download it.
Or just `rclone copy` it to a real disk (that's the mirror in [`03`](03-local-mirror.md)).

## Why NOT to work blindly on the mounted letter

- `find`/`du` hang (hydration).
- A bare **move out** of the mounted folder **deletes the file from the cloud**.
- Bulk delete stalls and leaves phantom shells.
- Path depth + `MAX_PATH 260` failures are easy to hit.

**Rule:** use rclone (API-direct) for inventory, move, copy, verify and delete.
Use the mounted letter only for casual, interactive single-file work.

## Drive for Desktop vs rclone — quick guide

| Task | Use |
|---|---|
| Inventory / measure | rclone (`lsf`, `size --json`) |
| Move/reorg within an account | rclone (`move`, server-side) |
| Copy between accounts | rclone (`--server-side-across-configs`) |
| Mirror to disk / export natives | rclone (`copy --drive-export-formats`) |
| Casual open/edit a single file | Drive for Desktop (mounted letter) |

Next: [`10-space-and-distribution.md`](10-space-and-distribution.md).
