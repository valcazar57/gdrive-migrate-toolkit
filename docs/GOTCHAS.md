# GOTCHAS — the traps that cost time

Every one of these was learned the hard way. Read before you touch a real account.

## Google Drive behavior

- **"Move" out of Drive deletes the cloud copy.** Drive for Desktop / a bare `mv`
  out of a synced folder removes the file from the cloud. Always **copy → verify →
  delete-to-trash**, never a bare move out.
- **Google-native files are cloud-only pointers** (`.gdoc/.gsheet/.gslides`, ~197
  bytes, rclone `Size == -1`). The content lives only in the cloud.
  - **Preserved** by `rclone move` (intra-account) and
    `rclone copy --server-side-across-configs` (cross-account, owned only).
  - **Exported** to Office by `rclone copy --drive-export-formats docx,xlsx,pptx`
    (any download to disk).
  - **Cannot** be copied by robocopy (exit 8) or `cp` (0-byte garbage). They survive
    only as a native-in-Drive or as an export.
- **Non-owned items 404 on server-side copy.** Much of "My Drive" is shared /
  uploaded by others. `files.copy` only copies what the account **owns**; the rest
  404s server-side but **downloads fine directly**. Not zombies. (A few may be true
  zombies — API-listed but 404 by every method; count, flag `REVIEW`, move on.)
- **The 30-day trash counts against quota** until emptied (or auto-purge). It's a
  safety net, **not** a backup. `rclone backend untrash` fails if the parent folder
  was deleted → restore via web UI or re-copy from your mirror.
- **Never touch `Shared drives` / `.shortcut-targets-by-id`** — out of scope.

## Rate limits & orchestration

- **Never two rclone processes against the SAME account at once** → HTTP 429,
  instant failures often with no log. Serialize per source account. Relay from the
  **local mirror** (not the source) to avoid contention.
- **Reparenting/copying thousands of files is slow** (~1 API call each at
  `--tpslimit 10` + 429 backoff). A few thousand files ≈ 30 min. If your shell times
  out but the post-check shows source==0 / dest matches, it **completed** — log it.

## Windows / shell

- **Drive for Desktop = virtual files.** Recursive `find`/`du`/`dir /s` over a
  mounted letter **hangs** (hydration). Bulk `rm -rf` stalls and leaves phantom
  `desktop.ini` shells. Use rclone (API-direct) or the Drive web UI for bulk delete.
- **`rclone size`/`lsjson -R` over huge folders (>~2k files) hangs** / exhausts
  wall-time. Measure **per block**, big blocks each in their own call with a
  generous timeout.
- **`subprocess` can return `stdout=None` for large outputs** in this environment.
  Redirect large listings to a file and re-read (the scripts do this via
  `capture_to_file`).
- **MAX_PATH 260.** Mirroring deep paths under another folder can fail. Move blocks
  to a **short** destination (shortens internal paths) instead of nesting deeper.
- **One-letter rclone remotes are eclipsed by Windows drive letters** (`j:` = drive
  J:). Name remotes with **2+ letters**.
- **`python3` here is the Windows Python** (no MSYS `/tmp`). Keep glue in rclone +
  plain Python with paths both understand.
- **Pass rclone args as a LIST, not a shell string.** Paths with `|`, accents, `()`
  or trailing spaces are valid in Drive and break naive shell quoting. The scripts
  do this; if you script your own, do the same.
- **`MSYS_NO_PATHCONV=1`** when calling Windows tools from Git Bash, or MSYS rewrites
  flags like `/E` into `L:/`-style paths.

## Verification

- **Verify by content (hash) or count, never by stale path** after renaming.
- **Count deficits are usually not loss**: dangling shortcuts (broken links) +
  duplicate names (Drive allows homonyms; destination collapses to one). Confirm
  with `rclone check --one-way SRC DST`.
- **`rclone move` leaves empty source folders.** Proof of completion is
  `rclone lsf -R --files-only <source> == 0`, not "no folders left". Close with
  `rclone purge <source> --drive-use-trash=true`.
- **Exact-hash dedup misses near-identical media** (re-encodes/resizes have a
  different hash). And **source ≠ export** (`.psd`/`.png`, `.xlsx`/`.pdf`) — keep
  both. Trees of tiny identical files → false orphans by hash; compare by path.

## robocopy (if you use it instead of rclone)

- Forces hydration (real download). Exit codes are a **bitmask**: 1=copied OK,
  8=failures, **9 (=8+1)=copied OK + some failures**. An exit 8/9 is not automatic
  alarm — check the log: if `Bytes Copied == Total` and the only ERRORs are
  Google-native (`ERROR 1 0x00000001`), the byte copy is 100%. robocopy simply
  cannot materialize natives. Prefer rclone for anything involving natives.
