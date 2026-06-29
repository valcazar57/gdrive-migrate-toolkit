# 08 — Upload disk → Drive (and download back)

The reverse of the mirror: push local files **up** to any folder in any Drive
account. Also covers resuming and round-tripping.

## Upload a local folder to any Drive folder

```bash
# Create the destination path if needed (parents are created)
rclone mkdir "accountA:Clients/Brand1/Deliverables"

# Upload (dry-run first)
rclone copy "D:/work/Brand1/Deliverables" "accountA:Clients/Brand1/Deliverables" \
  --exclude desktop.ini --transfers 8 --tpslimit 10 --drive-pacer-min-sleep 10ms --progress --dry-run

# Apply
rclone copy "D:/work/Brand1/Deliverables" "accountA:Clients/Brand1/Deliverables" \
  --exclude desktop.ini --transfers 8 --tpslimit 10 --drive-pacer-min-sleep 10ms --progress
```

- `rclone copy` adds/updates; it never deletes at the destination. Use
  `rclone sync` only when you deliberately want the destination to mirror the
  source **exactly** (it WILL delete extra files at the destination — dangerous).
- Idempotent: re-running uploads only what changed. Safe to resume after an
  interruption (rclone restarts incomplete files).

## Will uploaded Office files become Google-native?

By default, **no** — an uploaded `.docx`/`.xlsx`/`.pptx` stays an Office file in
Drive. To convert on upload to native Docs/Sheets/Slides:

```bash
rclone copy "D:/work/docs" "accountA:Docs" --drive-import-formats docx,xlsx,pptx
```

Use this only if you want editable Google Docs; otherwise keep them as Office files.

## Download back (the inverse)

That's the local mirror — see [`03-local-mirror.md`](03-local-mirror.md):

```bash
rclone copy "accountA:Some Folder" "D:/MIRROR/Some Folder" \
  --drive-export-formats docx,xlsx,pptx --exclude desktop.ini --progress
```

## Disk → Drive vs Drive → Drive (which preserves natives?)

| Operation | Tool | Google-native |
|---|---|---|
| Disk → Drive (upload) | `rclone copy` (`--drive-import-formats` optional) | created as Office unless you import-convert |
| Drive → Disk (download/mirror) | `rclone copy --drive-export-formats` | **exported** to Office |
| Drive → Drive same account (reorg) | `rclone move` | **preserved** (server-side reparent) |
| Drive → Drive cross account | `rclone copy --server-side-across-configs` | **preserved** (owned files only) |

So: a native survives as a true native **only** when it stays inside Drive. Once it
hits the local filesystem it's an Office export. Plan accordingly.

Next: [`09-drive-for-desktop.md`](09-drive-for-desktop.md).
