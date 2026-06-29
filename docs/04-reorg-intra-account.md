# 04 — Intra-account reorg (server-side move)

When an account already holds the content but it's **badly structured** (root
dumping ground, a `00 - INBOX` to redistribute, blocks with ugly names) and you're
NOT deleting the source: reorganize **in place**.

## Why `rclone move` intra-account is safe and instant

Same remote on source and destination = Drive does a **server-side reparent** of
metadata. It only changes the file's "parent":
- **Instant** — no download, no re-upload.
- **Preserves Google-native** (`Size=-1`; the Doc/Sheet stays native and editable,
  it is NOT exported). This is the opposite of moving *between* accounts.
- Cross-account is **blocked by default** in `reorg_move.py` (a cross-account
  `move` copies-then-deletes per file). Use [`evacuate.py`](05-evacuation-cross-account.md);
  only for OWNED files, `--allow-cross-account-move` opts in (it adds
  `--server-side-across-configs`).

## Recipe

1. **Audit one level** (never blindly recursive):
   ```bash
   rclone lsf --dirs-only accountA:
   rclone size --json "accountA:00 - INBOX/SomeBlock"
   ```
2. **Decide the taxonomy with the owner.** Align to the account's live convention
   (e.g. `BRAND | PLATFORM | CATEGORY`). Fix the decision before moving.
3. **Write the move table** `templates/move_table.example.csv` → your own
   `move_table.csv` with `group;source;dest` rows. One block = one row.
4. **Dry-run, then apply:**
   ```bash
   # dry-run (default): shows what would move, changes nothing
   python scripts/reorg_move.py --table move_table.csv --src-remote accountA: --dst-remote accountA:
   # apply
   python scripts/reorg_move.py --table move_table.csv --src-remote accountA: --dst-remote accountA: --apply
   ```
5. **Verify each row.** The script checks the destination received the count AND
   the source is left at **0 files** (`lsf -R --files-only` == 0). It writes
   `changes_reorg_YYYYMMDD.csv`.

## GOTCHA: empty source folders remain

`rclone move` moves the **content** but leaves the **source folders empty** (it
doesn't delete empty dirs without `--delete-empty-src-dirs`). So "no folders left"
is NOT the proof of completion — `lsf -R --files-only <source> == 0` is.

Clean up the empty shell of the inbox at the end:

```bash
rclone purge "accountA:00 - INBOX" --drive-use-trash=true   # reversible 30 days
```

## Performance notes

- Reparenting thousands of files = one API call each at `--tpslimit 10`, plus 429
  backoff. A few thousand files can take ~30 min. If your shell times out but the
  post-check shows source==0 and dest matches, it **completed** — log the row by hand.
- Paths with `|`, accents, `()` or trailing spaces are valid in Drive. The scripts
  pass args as a list (no shell), so these are handled.

Next: [`05-evacuation-cross-account.md`](05-evacuation-cross-account.md).
