# 05 — Cross-account evacuation (2 passes)

Empty a whole Drive/Workspace account by redistributing its content to other
accounts and a local disk. The complication: in "My Drive", a large share is
usually **not owned** by you (shared / uploaded by others), and the fast
server-side copy can't move what you don't own.

## The two-pass method (per block)

```
Pass 1 (server-side):  rclone copy SRC DST --server-side-across-configs
    -> copies OWNED files cloud->cloud, FAST, preserves Google-native (Size=-1).
    -> NON-owned items 404 here. That's expected, not a zombie.

Pass 2 (relay):        rclone copy LOCAL_MIRROR DST --ignore-existing
    -> uploads the NON-owned files from your local mirror (docs/03),
       WITHOUT overwriting what pass 1 already placed.
```

Both passes are driven by the same table, with an extra `mirror` column:

```
group;source;dest;mirror
Brand1;accountA:Brand1;accountB:Inbox/Brand1;D:/MIRROR/Brand1
HR;accountA:HR;accountC:Inbox/HR;D:/MIRROR/HR
```

```bash
# dry-run both passes
python scripts/evacuate.py --table move_table.csv

# apply pass 1 (owned, server-side) for all blocks
python scripts/evacuate.py --table move_table.csv --pass 1 --apply

# apply pass 2 (non-owned, relay from local mirror)
python scripts/evacuate.py --table move_table.csv --pass 2 --apply
```

## GOLDEN RULE: one rclone per source account

**Never run two rclone processes against the same account at once** → HTTP 429,
instant failures, often with no log. The relay (pass 2) reads the local mirror,
not the source account, so it doesn't contend — that's why mirroring first
(docs/03) then relaying from disk is the efficient, throttle-free path.

## Why owned vs non-owned, and what 404 means

`files.copy` (server-side) only copies files the account **owns**. Shared/uploaded-
by-others files 404 server-side — but their **direct download works** (that's how
they ended up in your mirror). They are NOT lost/zombie files. A small number may
be true zombies (listed by the API but 404 by every method — storage lost / origin
account closed); count them, flag `REVIEW`, move on.

## Verify before deleting anything

```bash
python scripts/verify_counts.py --table move_table.csv --src-remote accountA: --dst-remote accountB: --out verify.csv
```

Small deficits are usually dangling shortcuts + duplicate names (see docs/03), not
loss. For certainty: `rclone check --one-way SRC DST`.

## Delete the source (reversible)

Only after the disk mirror is complete AND the destinations verify:

```bash
rclone purge "accountA:Brand1" --drive-use-trash=true   # to trash, 30-day net
```

Notes: the trash counts against quota until emptied (or auto-purges at 30 days);
`rclone backend untrash` fails if the parent folder was already removed (restore
via the web UI or re-copy from the mirror); non-owned files do NOT go to your trash
(their safety net is your mirror). Keep `_CONTROL/` until the very end.

Next: [`06-dedup-and-quarantine.md`](06-dedup-and-quarantine.md).
