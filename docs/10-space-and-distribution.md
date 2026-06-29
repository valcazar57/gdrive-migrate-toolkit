# 10 — Space & distribution planning

Before evacuating or merging, figure out **how much free space each account has**
and **what goes where**, so you never push a block into an account that can't hold
it.

## Measure free space per account

```bash
rclone about accountA:
rclone about accountB:
rclone about accountC:
```

`rclone about` prints `Total`, `Used`, `Free` (and `Trashed`). Build a table:

| account | total | used | free | trashed |
|---|---|---|---|---|
| accountA (to empty) | 30 GiB | 28 GiB | 2 GiB | 4 GiB |
| accountB | 2 TiB | 0.4 TiB | 1.6 TiB | — |
| accountC | 100 GiB | 60 GiB | 40 GiB | — |
| D:/MIRROR (disk) | 1 TiB | 0.3 TiB | 0.7 TiB | — |

> Remember: the **trash counts against quota** until emptied. If an account looks
> full, check `Trashed` — emptying the trash may free what you need.

## Measure each block to move

Per block in the source account (one at a time — never the whole tree):

```bash
rclone size --json "accountA:Brand1"
```

## The distribution rules

1. **Heaviest first.** Place the big blocks before the small ones; it's where you
   can run out of space.
2. **Group by affinity** (brand / entity / client), not by size alone — keep
   related material together in the destination.
3. **Never exceed the destination's free space.** Sum the blocks assigned to each
   destination and compare to its `Free`. Leave headroom (10–20%).
4. **Disk is the overflow.** Anything that doesn't fit a cloud account goes to the
   local mirror (`D:/MIRROR`), which is also your safety net.
5. **Fiscal/entity boundaries override tidiness.** Don't merge across legal entities
   just to balance space — flag `LEGAL_REVIEW`.

## Write the plan as the move table

Turn the decision into `templates/move_table.example.csv` → your `move_table.csv`:

```
group;source;dest;mirror
Brand1;accountA:Brand1;accountB:Inbox/Brand1;D:/MIRROR/Brand1
HR;accountA:HR;accountC:Inbox/HR;D:/MIRROR/HR
Misc;accountA:Misc;;D:/MIRROR/Misc          # disk-only (no cloud dest)
```

Then dry-run it with `evacuate.py` (docs/05) and check the destination counts grow
as expected before `--apply`. Re-measure `rclone about` after each big block to
confirm free space is tracking your plan.

## Worked example sketch

- accountA (30 GiB, to empty): Brand1 38 GiB won't fit anywhere small → split:
  heavy media → `D:/MIRROR` + accountB (1.6 TiB free); editable docs → accountB.
- HR (1.2 GiB) → accountC (40 GiB free), grouped with other ops material.
- Verify (`verify_counts.py`), then `rclone purge` source blocks to trash.

Back to the [README](../README.md) · all traps in [`GOTCHAS.md`](GOTCHAS.md).
