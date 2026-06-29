# 06 — Dedup & quarantine

Reduce clutter safely: identical files collapse to one canonical copy; everything
disposable goes to a **quarantine** folder, never straight to the trash.

## Quarantine, not deletion

Create `99_REVIEW/` at the root of the tidied tree. Move junk/duplicate folders
there with an **index prefix** to avoid name collisions and MAX_PATH blow-ups:

```
99_REVIEW/Q001__New folder
99_REVIEW/Q002__- copy
99_REVIEW/_DUPLICATES/D000001__some-file.psd
```

Log every move (`source;dest;action`) so it's reversible. The owner reviews
`99_REVIEW` at the end and may choose to **keep** it — respect that.

## Exact-hash dedup (the safe part)

Hash the whole **clean** tree (excluding `_CONTROL` and `99_REVIEW`), group by hash:

```bash
# On a local mirror (fast, no hydration). Git Bash / macOS / Linux.
find . -type f -not -path "./_CONTROL/*" -not -path "./99_REVIEW/*" -print0 \
  | xargs -0 sha256sum > hashes.txt

# Groups with more than one copy:
awk '{print $1}' hashes.txt | sort | uniq -c | sort -rn | awk '$1>1'
```

**Pick the canonical** by rules:
1. Penalize names containing `copy`, `new`, `delete`, `final_2`.
2. Then lower folder depth.
3. Then shorter path.
4. Creative work: the **final/approved** version + its **source** are both
   canonical (not duplicates of each other) — keep both.

Move the surplus copies to `99_REVIEW/_DUPLICATES/...` with a manifest
(`hash;kept_canonical;moved_copy;size`).

## What exact-hash dedup does NOT catch

- **Near-identical media**: re-encodes, trims, bitrate/resolution changes, re-exports
  have a **different hash** though they look/sound the same → `REVIEW`, never
  auto-delete. Perceptual similarity is a human call.
- **Source vs export**: `.psd`→`.png`, `.xlsx`→`.pdf`, `.docx`→`.pdf` are different
  content in different formats → keep both, not duplicates.
- **Trees of tiny identical files** (e.g. WordPress `.php/.js/.css`): many files
  share a hash, so a hash-set comparison gives **false orphans**. Verify those by
  **relative path** + counts instead.

## Google-native and 0-byte files

- Google-native are cloud pointers (`Size=-1`); they don't hash meaningfully on
  disk. Handle them in Drive (preserve via server-side move) or via their export.
- 0-byte files all share the empty hash (`e3b0c442...`) — treat them separately so
  they don't pollute dedup groups.

Next: [`07-verify-and-delete.md`](07-verify-and-delete.md).
