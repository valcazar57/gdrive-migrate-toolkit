# PLAYBOOK — Tidy, merge and evacuate a company Google Drive (reproducible)

A battle-tested process for reorganizing, merging, deduplicating and **evacuating**
Google Drive / Google Workspace accounts at scale, then redistributing the content
to other Drive accounts or local disks — **without losing data and reversibly**.

Reference environment: Windows + Git Bash (MSYS) + Google Drive for Desktop +
[rclone](https://rclone.org/). The method generalizes to macOS/Linux; only the
Drive-for-Desktop traps are Windows-specific.

> This document is anonymized. All account names, brands, clients and paths are
> placeholders (`accountA:`, `Brand1`, `Client1`, `D:/MIRROR`, ...).

---

## 0. Principles (non-negotiable)

1. **Read-only first.** Inventory and understand before touching anything.
2. **Copy, never move *from* Drive.** Moving a file *out* of a synced folder
   DELETES it from the cloud. Always migrate with a COPY.
3. **Nothing is truly deleted (yet).** Disposable items go to a **quarantine**
   (`99_REVIEW`), not the trash. Permanent deletion = final phase, with explicit
   confirmation, batch by batch.
4. **Everything logged and reversible.** Each operation to a CSV
   (source → dest → action). Reversal = inverse CSV.
5. **Small batches.** Dry-run → collision check → approval → execute → verify
   counts → next.
6. **Confidentiality.** Minimize reading file contents. Don't upload anything to
   external services. Flag `LEGAL_REVIEW` (contracts, GDPR, HR, taxes, lawsuits).
7. **When in doubt, keep it and note it.** Never invent dates, owners or categories.

## 1. Hard-won technical traps (the ones that cost time)

- **Drive for Desktop = virtual files.** Recursive `find`/`du` over a mounted
  Drive letter HANGS because it hydrates (downloads) cloud placeholders. Walk
  **folder by folder** with `timeout`, or force download first. (rclone talks to
  the API directly and avoids this — prefer rclone for listing/measuring.)
- **`rclone about accountX:`** is the sanity check that a remote points at the
  cloud (small cloud quota) and not at your local disk (~TBs).
- **Google-native files** (`.gdoc`/`.gsheet`/`.gslides`) are **~197-byte pointers**;
  the content lives only in the cloud. rclone reports them with `Size == -1`.
  - **move/copy intra-account or server-side PRESERVES** them (stay native/editable).
  - **Going to disk EXPORTS** them to `.docx/.xlsx/.pptx` (use `--drive-export-formats`).
  - **robocopy/cp CANNOT** copy them (robocopy = exit 8; cp = 0-byte garbage).
- **MAX_PATH 260 on Windows.** Mirroring deep paths under another folder can blow
  past 260 and fail. Move folders **as a block** to a short destination, which
  *shortens* internal paths instead of lengthening them.
- **`python3` in this kind of environment is the Windows one**: it doesn't see the
  MSYS `/tmp`. For glue scripting, stay in rclone + plain Python with paths both
  understand.
- **File-by-file `mv`/`stat` loops are slow** (hundreds/thousands → timeout).
  Chunk and **resume** from the last logged index (idempotency by index).
- **Deleting from a mounted Drive with local `rm -rf` STALLS** (it hydrates every
  file first) and leaves empty shells with phantom `desktop.ini`. For **bulk**
  deletion use the **Drive web UI** (cloud-side, instant) or `rclone purge`
  (see §2 final phase); local placeholders clean up on sync.
- **Never two rclone processes against the SAME account at once** → HTTP 429,
  instant failures with no log. Serialize per source account.
- **stdout=None for large outputs.** `subprocess.run(..., capture_output=True)`
  can return `stdout=None` for big listings in this environment. Redirect large
  listings to a file and re-read it (the scripts here already do this).
- **`rclone size`/`lsjson -R` recursive over huge folders (>~2k files) hangs** or
  exhausts the kernel wall-time. Measure **per block**, never the whole tree;
  large blocks each in their own call with a generous timeout.

## 2. Step-by-step flow

### Phase 0 — Inventory (read-only)
- Structure, per-folder counts, formats, sizes. Detect how many entities/companies
  are mixed together. `rclone lsf --dirs-only accountA:` one level at a time.
- Flag candidates: junk folders, apparent duplicates, Google-native, sensitive
  (`LEGAL_REVIEW`).
- Save everything in a control folder (`_CONTROL`). See `scripts/detect_natives.py`.

### Phase 1 — Safe mirror to disk
- `mirror_account.py` (`rclone copy remote: D:/MIRROR --drive-export-formats ...`).
  This grabs everything including non-owned/shared content, and exports natives.
- This local mirror is the **real safety net** and the source of the cross-account
  relay (Phase 5 pass 2). Verify counts vs source; keep the log.

### Phase A — Regenerable junk
- Delete `desktop.ini` (and `Thumbs.db`, `.DS_Store`). The only "safe" deletion.
  Log it anyway. (`--exclude desktop.ini` is on by default in the scripts.)

### Phase B — Quarantine junk folders
- Detect by name: `Delete`, `No good`, `- copy`, `New folder`, `Takeout` (verify
  Takeout by hash — it's often the *most complete* copy, not junk).
- Compute only the **top-most** junk folders (junk inside junk → move only the outer).
- Move to `99_REVIEW/Q001__<name>`, `Q002__…` (index avoids name collisions and
  MAX_PATH). CSV with the full source path.

### Phase C — Deduplicate and unify
- SHA-256 of the whole clean tree. Group by hash.
- **Pick the canonical** by rules: penalize "copy/new/delete" names, then lower
  depth, then shorter path. Creative work: the **final/approved** version + its
  source are both canonical (not duplicates of each other).
- Move surplus copies to `99_REVIEW/_DUPLICATES/D000001__<name>` with a manifest.
- Exact-hash dedup does NOT catch "near-identical" media (re-encodes, re-exports,
  resizes have a different hash) → `REVIEW`, never auto-delete.

### Phase D — Separate entities
- One root folder per company/person (`01 COMPANY A`, `02 COMPANY B`, `03 SOLE-TRADER`).
- Extract what's buried inside another entity (move the block, log, collision check).
- **Moving files between fiscal entities has tax implications** → explicit approval
  + `LEGAL_REVIEW`. Don't reassign an invoice just to "tidy up".

### Phase E — Rename FOLDERS (not files)
- High impact / low risk: renaming a folder doesn't move files; undo = rename back.
  Intra-account this is a server-side reparent (instant, preserves natives).
- Rename **inner-to-outer** (children before parents) or re-list after each level.
- **Don't rename files** whose name is already informative (e.g. invoices encoding
  date+vendor+amount). Camera/screenshot names (`IMG_2381`) DO benefit from renaming.

### Phase 5 — Reorganize / evacuate with rclone (the core engine)

**Intra-account reorg** (`scripts/reorg_move.py`): same remote on source and dest
→ `rclone move` does a server-side reparent. Instant, preserves natives. Driven by
a CSV table of `(group, source, dest)`. The proof of "all moved" is
`rclone lsf -R --files-only <source> == 0`, NOT the absence of empty folders
(`rclone move` leaves empty source dirs behind). Close with
`rclone purge <inbox> --drive-use-trash=true`.

**Cross-account evacuation at scale** (`scripts/evacuate.py`): empty a whole
account by redistributing to others + disk. Two passes per block:
1. `rclone copy SRC DST --drive-server-side-across-configs` — copies **owned**
   files cloud→cloud, preserves natives. Non-owned items 404 here (that's expected,
   not a zombie).
2. `rclone copy LOCAL_MIRROR DST --ignore-existing` — uploads the **non-owned**
   files from the local mirror, without overwriting pass 1.

**Single folder to another account preserving natives:**
`rclone copy "A:Folder" "B:Folder" --drive-server-side-across-configs` (no
`--drive-export-formats`, which would export and break the native). Owned files only.

### Final phase — Permanent deletion (only with absolute confirmation)
- Review `99_REVIEW` with the owner. The owner may choose to **keep** verified-safe
  quarantine — respect it.
- Delete the source **only** after verifying the disk copy is complete and natives
  are exported/preserved.
- Use `rclone purge account:Folder --drive-use-trash=true` (whole folder to trash,
  recoverable for **30 days**) or the Drive web UI for bulk. The trash **counts
  against quota** until emptied (or auto-purges at 30 days).
- **NEVER touch** `Shared drives` or `.shortcut-targets-by-id` (out of scope).

## 3. Integrity verification (every batch)

- Total file count before/after must add up: `clean + quarantine = total`.
- After dedup: zero hash groups with >1 copy remain in the clean tree.
- **Verify by CONTENT (hash) or COUNT, never by path** if folders were renamed in
  between (path manifests go stale). For owned binary/media, hash is perfect; for
  trees of thousands of tiny identical files, compare by **relative path** + counts
  (many files share a hash → false orphans).
- Gate before any permanent deletion: the set of hashes to delete must be
  **contained** in the clean tree's hash set → 0 orphans = no possible loss.
- Small count deficits after a cross-account copy are usually **dangling shortcuts**
  + **duplicate names** (Drive allows homonyms; the destination collapses to one) —
  not data loss. Confirm with `rclone check --one-way SRC DST`.

## 4. Deliverables to leave on the account/disk
- A `README — STATE & ORGANIZATION.md` at the root of the tidied folder.
- In `_CONTROL/`: `changes_YYYYMMDD.csv`, `duplicates_YYYYMMDD.csv`, inventory,
  plan, export checklist, result.

## 5. Generalize to ALL material types and company areas

The method (inventory → quarantine → hash dedup → separate → rename folders →
verified final deletion) works for any area (marketing, legal, HR, product,
finance) and any format. The **nuances by type** change:

- **Audio/Video**: heavy files → exact dedup gives the biggest disk win, do it
  first. But re-encodes/trims/bitrate changes have a **different hash** though they
  look/sound identical → `REVIEW`, never auto-delete. Editing projects
  (`.prproj`, `.aep`, `.drp`, `.fcpxml`) **link** media by relative path: moving
  the media **breaks** the timeline → move project + media **as a block**. Keep the
  **master/final render** *and* the source project; both are canonical.
- **Graphics/images**: distinguish **editable source** (`.psd`, `.ai`, `.fig`) from
  **export** (`.png`, `.jpg`, `.pdf`). NOT duplicates — keep both. Visual equality
  ≠ byte equality (a human decides perceptual similarity).
- **Text docs**: `v1/v2/final/FINAL_2` = history, not duplicates → keep the last,
  send the rest to `REVIEW`. Watch for personal/legal data → `LEGAL_REVIEW`.
- **Spreadsheets**: an `.xlsx` with formulas ≠ its `.csv`/`.pdf` export (loses
  formulas). `.xlsm` macros / external links can break on move.
- **Archives/backups** (`.zip`, dated backups): often full copies → big candidates,
  but open/verify first; a newer backup may be a superset of the old one.

### Criterion tuning by domain
- **Rename files**: NO in admin (the name already encodes date+vendor+amount). YES
  in media/graphics (camera/capture names aren't informative).
- **Root structure**: by fiscal entity in admin; by **area → project → date/client**
  in marketing/production. Pick the taxonomy the owner searches by.
- **What is canonical**: in admin, the shortest path outside quarantine. In creative,
  the **final/approved** version + its source, even if the path is longer.

## 6. Mistakes not to repeat
- Don't assume "Takeout"/"export"/"copy" = junk. Verify by hash.
- Don't mirror deep paths (MAX_PATH). Move as a block to a short destination.
- Don't run recursive `find`/`du`/`lsjson -R` over a huge Drive: it hangs.
- Don't move *from* Drive (deletes the cloud). Copy.
- Don't rename files whose name is already informative.
- Don't trust a Google-native backup made with robocopy/cp.
- Don't verify by path after renaming: verify by hash/count (content).
- Don't dedup media by hash and assume it covers "near-identical".
- Don't delete the source without 0 orphans and natives exported/preserved. The
  30-day trash is the net, not the first line.
- Don't run two rclone processes against the same account at once (429).
- Don't move/rename **live editing folders** (`.prproj`/`.drp` link media by path).

## 7. Where each topic lives in this repo

| Topic | Doc |
|---|---|
| Principles & agent rules | `docs/00-principles.md`, `AGENTS.md` |
| Install & configure rclone | `docs/01-setup-rclone.md` |
| Inventory without hanging Drive | `docs/02-inventory.md` |
| Local mirror (download + export natives) | `docs/03-local-mirror.md` |
| Intra-account reorg (server-side move) | `docs/04-reorg-intra-account.md` |
| Cross-account evacuation (2 passes) | `docs/05-evacuation-cross-account.md` |
| Dedup & quarantine | `docs/06-dedup-and-quarantine.md` |
| Verify & delete (reversible) | `docs/07-verify-and-delete.md` |
| Upload disk → Drive | `docs/08-disk-to-drive.md` |
| Google Drive for Desktop (streaming vs mirror) | `docs/09-drive-for-desktop.md` |
| Space & distribution planning | `docs/10-space-and-distribution.md` |
| All the traps | `docs/GOTCHAS.md` |
