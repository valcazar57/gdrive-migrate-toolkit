#!/usr/bin/env python3
"""evacuate.py - Empty a Drive account, redistributing to other accounts + disk.

Much of "My Drive" is usually NOT owned by you (shared / uploaded by others).
The server-side copy (`files.copy`) 404s on non-owned items, but the direct
download works. Hence the TWO-PASS METHOD per block:

  Pass 1 (server-side): rclone copy SOURCE DEST --server-side-across-configs
      -> copies OWNED files cloud->cloud and PRESERVES Google-native (Size=-1).
  Pass 2 (relay):       rclone copy LOCAL_MIRROR DEST --ignore-existing
      -> uploads NON-owned files from the local mirror (mirror_account.py),
         without overwriting what pass 1 already put.

GOLDEN RULE: never two rclone processes against the SAME account at once
(-> HTTP 429). This script is serial (one subprocess at a time); even so, do not
run it in parallel with another rclone touching the same accounts.

Table (templates/move_table.example.csv, columns):
    group;source;dest;mirror
  - source = path in the account being emptied (e.g. accountA:Block)
  - dest   = path in the destination account (e.g. accountB:Inbox/Block)
  - mirror = equivalent local path for pass 2 (e.g. D:/MIRROR/Block); optional

DRY-RUN BY DEFAULT.
"""
from __future__ import annotations

import argparse
import sys

import common as c


def parse_args():
    ap = argparse.ArgumentParser(description="Evacuate a Drive account in 2 passes (owned server-side / non-owned relay).")
    ap.add_argument("--table", required=True, help="';'-delimited CSV group;source;dest;mirror")
    ap.add_argument("--src-remote", default=None, help="Default remote for 'source'")
    ap.add_argument("--dst-remote", default=None, help="Default remote for 'dest'")
    ap.add_argument("--pass", dest="phase", choices=["1", "2", "both"], default="both",
                    help="Which pass to run: 1=server-side, 2=local relay, both")
    ap.add_argument("--log", default=None, help="Changes CSV (default: changes_evacuation_YYYYMMDD.csv)")
    ap.add_argument("--apply", action="store_true", help="Actually run (without it: dry-run)")
    ap.add_argument("--timeout", type=int, default=7200, help="Timeout per copy in seconds (default 7200)")
    ap.add_argument("--rclone", default=None, help="Path to the rclone binary")
    return ap.parse_args()


HEADER = ["date", "group", "pass", "source", "dest", "n_source", "n_dest", "status", "mode"]


def do_copy(rclone, src, dst, extra, timeout, apply):
    args = ["copy", src, dst] + c.STD_FLAGS + c.exclude_args(c.DEFAULT_EXCLUDES) + extra
    if not apply:
        args.append("--dry-run")
    rc, _, err = c.run_rclone(rclone, args, timeout=timeout, capture_to_file=True)
    return rc, err


def main():
    a = parse_args()
    rclone = c.find_rclone(a.rclone)
    c.banner(a.apply)
    log = a.log or f"changes_evacuation_{c.today()}.csv"
    rows = c.read_table(a.table)
    if not rows:
        sys.exit("Empty table (columns group;source;dest;mirror?).")

    for i, r in enumerate(rows, 1):
        group = r.get("group", f"row{i}")
        src = c.qualify(r.get("source", ""), a.src_remote)
        dst = c.qualify(r.get("dest", ""), a.dst_remote)
        mirror = r.get("mirror", "").strip()
        print(f"\n[{i}/{len(rows)}] {group}")

        # ---- Pass 1: server-side (owned, preserves natives) ----
        if a.phase in ("1", "both"):
            n0 = c.rclone_size_or_none(rclone, src, timeout=a.timeout)
            n0c = n0["count"] if n0 else 0
            print(f"  P1 server-side: {src} -> {dst}  (source {n0c} obj)")
            rc, err = do_copy(rclone, src, dst, ["--server-side-across-configs"], a.timeout, a.apply)
            nd = c.rclone_size_or_none(rclone, dst, timeout=a.timeout) if a.apply else None
            ndc = nd["count"] if nd else ""
            status = "dry-run" if not a.apply else ("ok" if rc == 0 else f"REVIEW(rc={rc},404=non-owned)")
            if err.strip() and a.apply:
                print("     stderr:", err.strip().splitlines()[-1])
            c.append_csv(log, HEADER, [c.now_iso(), group, "1", src, dst, n0c, ndc, status,
                                       "apply" if a.apply else "dry-run"])

        # ---- Pass 2: relay from local mirror (non-owned) ----
        if a.phase in ("2", "both"):
            if not mirror:
                print("  P2 relay: no 'mirror' column -> SKIP (non-owned not recoverable without a mirror).")
            else:
                print(f"  P2 relay: {mirror} -> {dst}  (--ignore-existing)")
                rc, err = do_copy(rclone, mirror, dst, ["--ignore-existing"], a.timeout, a.apply)
                nd = c.rclone_size_or_none(rclone, dst, timeout=a.timeout) if a.apply else None
                ndc = nd["count"] if nd else ""
                status = "dry-run" if not a.apply else ("ok" if rc == 0 else f"ERROR(rc={rc})")
                if err.strip() and a.apply:
                    print("     stderr:", err.strip().splitlines()[-1])
                c.append_csv(log, HEADER, [c.now_iso(), group, "2", mirror, dst, "", ndc, status,
                                           "apply" if a.apply else "dry-run"])

    print(f"\nLog -> {log}")
    print("Remember: verify with verify_counts.py before deleting the source, and delete")
    print("to trash with `rclone purge account:Block --drive-use-trash=true` (30-day net).")
    if not a.apply:
        print("This was DRY-RUN.")


if __name__ == "__main__":
    main()
