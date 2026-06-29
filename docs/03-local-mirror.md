# 03 — Local mirror (download + export natives)

Before touching anything destructive, make a **verified local mirror** of the
account on a disk with enough free space. This is the real safety net (the 30-day
Drive trash is *not* a backup) and the source for the cross-account relay
([`05-evacuation-cross-account.md`](05-evacuation-cross-account.md) pass 2).

## Command

```bash
python scripts/mirror_account.py --remote accountA: --dest D:/MIRROR --apply
```

Under the hood:

```bash
rclone copy accountA: D:/MIRROR \
  --drive-export-formats docx,xlsx,pptx \
  --exclude desktop.ini \
  --transfers 8 --tpslimit 10 --drive-pacer-min-sleep 10ms --progress
```

Key points:
- `rclone copy` (direct download) grabs **everything, including non-owned/shared**
  content — unlike server-side copy, which 404s on non-owned items.
- `--drive-export-formats docx,xlsx,pptx` **exports Google-native** to Office,
  because they go to cold disk and have no byte-stream to copy as-is. (Format
  fidelity is acceptable for a cold archive; to keep a native *editable* you must
  keep it inside Drive — see [`04`](04-reorg-intra-account.md).)
- Idempotent: re-running only fetches what's missing.

## Verify

```bash
# Count source vs mirror per block
python scripts/verify_counts.py --src "accountA:Some Block" --dst "D:/MIRROR/Some Block"
```

Counts may differ slightly and still be fine:
- Exported natives count as 1 Office file (1:1 with the source pointer).
- **Dangling shortcuts** (broken links) can't be downloaded — not data loss.
- **Duplicate names**: Drive allows two files with the same name in a folder; a
  local filesystem collapses them to one. Not data loss, but note it.

For byte-level certainty on owned binaries:

```bash
rclone check --one-way accountA:Block D:/MIRROR/Block
```

## What to exclude

Huge backups of tiny files already archived elsewhere (e.g. a WordPress backup of
thousands of `.php/.js/.css`) slow the mirror to a crawl. Exclude them and archive
separately:

```bash
python scripts/mirror_account.py --remote accountA: --dest D:/MIRROR \
  --exclude "wp-backup/**" --exclude "node_modules/**" --apply
```

Keep the run log. The mirror plus the changes CSVs are what make the whole
operation reversible. Next: [`04-reorg-intra-account.md`](04-reorg-intra-account.md).
