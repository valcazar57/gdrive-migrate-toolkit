# 07 — Verify & delete (reversible)

The safety gate. Nothing permanent happens until counts/hashes prove no data can
be lost, and even then deletion is **to trash** (recoverable for 30 days).

## Verify by content or count, never by stale path

If you renamed folders along the way, path-based manifests go stale (the canonical
still exists, just at a new path). Verify by **hash** (content) or **count**:

```bash
# Count comparison per block (read-only)
python scripts/verify_counts.py --table move_table.csv \
  --src-remote accountA: --dst-remote accountB: --out verify.csv
```

### The orphan gate (before any permanent deletion)

The set of hashes you're about to delete must be **contained** in the clean tree's
hash set. Zero orphans = no possible loss.

```bash
# hashes of the clean tree (local mirror)
find . -type f -not -path "./_CONTROL/*" -not -path "./99_REVIEW/*" -print0 \
  | xargs -0 sha256sum | awk '{print $1}' | sort -u > clean.txt
# hashes of what you'll delete
find 99_REVIEW/_DUPLICATES -type f -print0 \
  | xargs -0 sha256sum | awk '{print $1}' | sort -u > todelete.txt
# orphans (must be 0): in 'todelete' but NOT in 'clean'
comm -23 todelete.txt clean.txt | wc -l
```

`> 0` orphans → **hard stop**, investigate. Only `_DUPLICATES` (verified exact
dups) is a deletion candidate; `Qxxx` junk folders may contain unique files → they
get their own review, not the bulk sweep.

## Count deficits are usually not loss

After a cross-account copy, a small destination shortfall is almost always:
- **dangling shortcuts** (broken links — nothing to copy), and
- **duplicate names** (Drive allows homonyms in a folder; the destination/local
  filesystem collapses them to one).

Confirm with `rclone check --one-way SRC DST` (md5). If unique files are genuinely
missing, merge them first with `rclone copy SRC DST --ignore-existing`.

## Delete to trash (reversible)

```bash
rclone purge "accountA:Block" --drive-use-trash=true     # whole folder -> trash
rclone delete "accountA:" --max-depth 1                   # loose root files only
```

- The trash **counts against quota** until you empty it (or it auto-purges at 30
  days). Emptying frees the space.
- `rclone backend untrash <path>` fails if the parent folder was already removed →
  restore via the Drive web UI, or re-copy from your local mirror.
- For huge bulk deletes, the Drive web UI (cloud-side) is also instant. Local
  `rm -rf` over a mounted Drive stalls — avoid it (see [`GOTCHAS.md`](GOTCHAS.md)).

## Reversal (undo a move)

Each script writes `changes_*.csv` (`...;source;dest;...;status`). To undo, read
the rows with `status=ok` and run the inverse move `dest -> source`. Keep the CSVs
and the local mirror until the owner signs off.

Next: [`08-disk-to-drive.md`](08-disk-to-drive.md).
