# 02 — Inventory without hanging Drive

Goal: understand the structure (how many entities are mixed, where the weight is,
where the Google-native files are) **without** triggering a hydration hang.

## The cardinal rule: never list a huge tree recursively in one shot

`rclone size`/`lsjson -R` over a folder with >~2k files can hang or exhaust your
shell's wall-time. **Measure per block**, one level at a time.

```bash
# Top-level folders only (one level — safe and fast)
rclone lsf --dirs-only accountA:

# Count + size of ONE block (includes Google-native in the count)
rclone size --json "accountA:Some Block"

# One level deeper for a specific block
rclone lsf --dirs-only "accountA:Some Block"
```

For each big block, run `rclone size --json` in its own command with a generous
timeout. Build a small table by hand:

| block | count | size |
|---|---|---|
| Brand1 | 4,151 | 38 GiB |
| HR | 320 | 1.2 GiB |
| ... | ... | ... |

## Detect Google-native files

These are cloud-only pointers (`Size == -1`). They drive your strategy: a block
that is 100% binary can be copied by anything; a block with natives needs
rclone server-side (to preserve) or export (to disk).

```bash
python scripts/detect_natives.py --path "accountA:Some Block" --max-depth 3 --out natives.csv
```

`--max-depth` bounds the recursion so it won't hang on a giant block.

## Flag candidates (don't act yet)

While inventorying, mark — in notes, not by moving:
- Junk folders by name: `Delete`, `No good`, `- copy`, `New folder`, `Takeout`
  (Takeout is often the *most complete* copy — verify by hash, don't assume junk).
- Apparent duplicates (confirm later by hash).
- Sensitive material → `LEGAL_REVIEW` (contracts, PII, HR, taxes).

## Ownership matters (for cross-account work)

In "My Drive", a large share is often **not owned** by you (shared / uploaded by
others). You can't see ownership from `lsf` directly, but you'll discover it in
[`05-evacuation-cross-account.md`](05-evacuation-cross-account.md): server-side
copy 404s on non-owned items. Plan for the two-pass method from the start.

Save your inventory table and `natives.csv` in a `_CONTROL/` folder (kept out of
git — see [`../.gitignore`](../.gitignore)). Next: [`03-local-mirror.md`](03-local-mirror.md).
