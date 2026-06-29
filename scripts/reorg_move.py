#!/usr/bin/env python3
"""reorg_move.py - Reorganize a Drive driven by a CSV table (rclone move).

Primary case: INTRA-ACCOUNT REORG. Same remote on source and destination ->
Drive does a server-side *reparent* of metadata: instant, no download/re-upload,
and it PRESERVES Google-native files (they stay editable, they are NOT exported).

Secondary case: move ONE folder to ANOTHER account. This is BLOCKED by default
(cross-account `move` copies then deletes per file, against the copy -> verify ->
delete contract). evacuate.py is the safe path; if you really need it for OWNED
files only, pass --allow-cross-account-move (shared items 404 server-side anyway).

The table (templates/move_table.example.csv) has columns:
    group;source;dest
One row = one move of a whole block. Destinations are created automatically.

Per row: size source -> move (or --dry-run) -> verify the destination received
the count and the source is left at 0 files -> append to the CSV log.

DRY-RUN BY DEFAULT. Use --apply to execute.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

import common as c


def parse_args():
    ap = argparse.ArgumentParser(description="Reorganize a Drive with rclone move driven by a CSV.")
    ap.add_argument("--table", required=True, help="';'-delimited CSV with columns group;source;dest")
    ap.add_argument("--src-remote", default=None, help="Default remote for 'source' if the cell lacks one (e.g. accountA:)")
    ap.add_argument("--dst-remote", default=None, help="Default remote for 'dest' if the cell lacks one (e.g. accountA:)")
    ap.add_argument("--log", default=None, help="Changes CSV (default: changes_reorg_YYYYMMDD.csv)")
    ap.add_argument("--apply", action="store_true", help="Actually run (without it: dry-run)")
    ap.add_argument("--allow-cross-account-move", action="store_true",
                    help="Allow `move` between DIFFERENT accounts (unsafe: copies then "
                         "deletes per file). Default blocks it; use evacuate.py instead.")
    ap.add_argument("--timeout", type=int, default=3600, help="Timeout per move in seconds (default 3600)")
    ap.add_argument("--rclone", default=None, help="Path to the rclone binary")
    return ap.parse_args()


HEADER = ["date", "group", "source", "dest", "n_src_before", "n_dst_added",
          "n_src_after", "status", "mode"]


def main():
    a = parse_args()
    rclone = c.find_rclone(a.rclone)
    c.banner(a.apply)
    log = a.log or f"changes_reorg_{c.today()}.csv"

    rows = c.read_table(a.table)
    if not rows:
        sys.exit("Table has no usable rows (columns group;source;dest?).")

    ok = skipped = failed = review = 0

    for i, r in enumerate(rows, 1):
        group = r.get("group", f"row{i}")
        src = c.qualify(r.get("source", ""), a.src_remote)
        dst = c.qualify(r.get("dest", ""), a.dst_remote)
        if not src or not dst:
            print(f"[{i}/{len(rows)}] {group}: empty source/dest -> SKIP")
            skipped += 1
            continue
        cross = c.remote_of(src) != c.remote_of(dst)
        if cross and not a.allow_cross_account_move:
            print(f"[{i}/{len(rows)}] {group}: cross-account move BLOCKED "
                  f"({c.remote_of(src)}: -> {c.remote_of(dst)}:). Use evacuate.py "
                  f"(copy -> verify -> delete), or pass --allow-cross-account-move.")
            c.append_csv(log, HEADER, [c.now_iso(), group, src, dst, "", "", "",
                                       "ERROR(cross_account_blocked)", "apply" if a.apply else "dry-run"])
            failed += 1
            continue
        extra = ["--server-side-across-configs"] if cross else []
        if cross:
            print("            NOTE: cross-account `move` copies then DELETES each source "
                  "file as it goes (owned files only).")

        try:
            n_src = c.rclone_size(rclone, src, timeout=a.timeout)
        except c.RcloneError as e:
            print(f"[{i}/{len(rows)}] {group}: cannot read source -> ERROR (not skipped)")
            print("            ", e)
            c.append_csv(log, HEADER, [c.now_iso(), group, src, dst, "", "", "",
                                       "ERROR(source_unreadable)", "apply" if a.apply else "dry-run"])
            failed += 1
            continue
        if n_src is None:
            # Source truly does not exist (already moved) -> clean idempotent skip.
            print(f"[{i}/{len(rows)}] {group}: source not found (already moved?) -> SKIP")
            c.append_csv(log, HEADER, [c.now_iso(), group, src, dst, "", "", "",
                                       "skip_no_source", "apply" if a.apply else "dry-run"])
            skipped += 1
            continue
        n_src_count = n_src["count"]
        print(f"[{i}/{len(rows)}] {group}: source {n_src_count} obj / {c.human(n_src['bytes'])}")
        print(f"            {src}  ->  {dst}")
        n_dst_before = 0
        if a.apply:
            try:
                before = c.rclone_size(rclone, dst, timeout=a.timeout)
            except c.RcloneError as e:
                print(f"            cannot measure destination -> REVIEW (move skipped): {e}")
                c.append_csv(log, HEADER, [c.now_iso(), group, src, dst, n_src_count, "", "",
                                           "REVIEW(dest_premeasure_failed)", "apply"])
                review += 1
                continue
            n_dst_before = before["count"] if before else 0

        args = ["move", src, dst] + c.STD_FLAGS + c.exclude_args(c.DEFAULT_EXCLUDES) + extra
        if not a.apply:
            args.append("--dry-run")
        try:
            rc, _, err = c.run_rclone(rclone, args, timeout=a.timeout, capture_to_file=True)
        except subprocess.TimeoutExpired:
            # Not necessarily a failure: reparenting thousands of files can exceed
            # the timeout and still complete. We verify below.
            print("            (move timed out; verifying real state anyway)")
            rc, err = -1, "timeout"

        if not a.apply:
            c.append_csv(log, HEADER, [c.now_iso(), group, src, dst, n_src_count, "", "", "dry-run", "dry-run"])
            print("            DRY-RUN: nothing moved.")
            ok += 1
            continue

        # Post-move verification (real run).
        try:
            n_dst = c.rclone_size(rclone, dst, timeout=a.timeout)
            n_left = c.rclone_count_files(rclone, src, timeout=a.timeout)
        except c.RcloneError as e:
            print("            verify failed:", e)
            c.append_csv(log, HEADER, [c.now_iso(), group, src, dst, n_src_count, "", "",
                                       "REVIEW(verify_error)", "apply"])
            failed += 1
            continue
        dst_after = n_dst["count"] if n_dst else 0
        n_left = 0 if n_left is None else n_left
        added = dst_after - n_dst_before
        if rc not in (0, -1):
            status = f"ERROR(rc={rc})"
            failed += 1
        elif n_left != 0:
            status = f"REVIEW(source_left={n_left})"
            failed += 1
        elif added != n_src_count:
            # Could be benign (collisions/dedup) or real loss -> never silent success.
            status = f"REVIEW(added={added}!=src={n_src_count})"
            review += 1
        else:
            status = "ok"
            ok += 1
        if err.strip():
            print("            stderr:", err.strip().splitlines()[-1])
        print(f"            added={added}  dest_total={dst_after}  source_left={n_left}  -> {status}")
        c.append_csv(log, HEADER, [c.now_iso(), group, src, dst, n_src_count, added, n_left, status, "apply"])

    print(f"\nSummary: ok={ok} skipped={skipped} review={review} failed={failed}. Log -> {log}")
    if not a.apply:
        print("This was DRY-RUN. Review the plan and re-run with --apply once approved.")
    sys.exit(1 if failed else (2 if review else 0))


if __name__ == "__main__":
    main()
