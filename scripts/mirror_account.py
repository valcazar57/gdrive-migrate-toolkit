#!/usr/bin/env python3
"""mirror_account.py - Local mirror of a Drive account (safety net).

Downloads ALL content of an account (or subfolder) to a local disk with
`rclone copy`. It also grabs NON-owned (shared) content, which the server-side
copy cannot move. Google-native files are EXPORTED to Office (.docx/.xlsx/.pptx)
because they go to cold disk - a native has no byte-stream to copy as-is.

This mirror is:
- the real safety net (better than the trash), and
- the source for pass 2 of evacuate.py (relay of non-owned files).

Idempotent: re-running only fetches what's missing. DRY-RUN BY DEFAULT.
"""
from __future__ import annotations

import argparse

import common as c


def parse_args():
    ap = argparse.ArgumentParser(description="Local mirror of a Drive account with rclone copy.")
    ap.add_argument("--remote", required=True, help="Source remote/account (e.g. accountA: or accountA:Subfolder)")
    ap.add_argument("--dest", required=True, help="Local destination folder (e.g. D:/MIRROR)")
    ap.add_argument("--export-formats", default="docx,xlsx,pptx",
                    help="Export formats for Google-native (default docx,xlsx,pptx)")
    ap.add_argument("--exclude", action="append", default=None,
                    help="Pattern to exclude (repeatable). desktop.ini is excluded by default")
    ap.add_argument("--apply", action="store_true", help="Actually run (without it: dry-run)")
    ap.add_argument("--timeout", type=int, default=0, help="Total timeout in seconds (0 = no limit)")
    ap.add_argument("--rclone", default=None, help="Path to the rclone binary")
    return ap.parse_args()


def main():
    a = parse_args()
    rclone = c.find_rclone(a.rclone)
    c.banner(a.apply)
    excludes = (a.exclude or []) + c.DEFAULT_EXCLUDES

    src = a.remote if ":" in a.remote.split("/", 1)[0] else a.remote + ":"
    timeout = a.timeout or None

    before = c.rclone_size(rclone, src, timeout=timeout)
    if before is None:
        print(f"WARNING: could not measure {src} (wrong remote? huge folder that hangs?).")
    else:
        print(f"Source {src}: {before['count']} obj / {c.human(before['bytes'])}")

    args = ["copy", src, a.dest,
            "--drive-export-formats", a.export_formats] + c.exclude_args(excludes) + [
            "--transfers", "8", "--tpslimit", "10", "--drive-pacer-min-sleep", "10ms",
            "--progress"]
    if not a.apply:
        args.append("--dry-run")

    print("rclone", " ".join(str(x) for x in args))
    rc, out, err = c.run_rclone(rclone, args, timeout=timeout)
    if out.strip():
        print(out.strip()[-2000:])
    if err.strip():
        print("stderr:", err.strip()[-2000:])

    if a.apply:
        after = c.rclone_count_files(rclone, a.dest, timeout=timeout)
        print(f"\nLocal {a.dest}: {after} files. (Note: exported natives count as 1 "
              "Office file; the count may not exactly match the source due to "
              "dangling shortcuts / duplicate names - see docs/GOTCHAS.md.)")
    else:
        print("\nDRY-RUN: nothing copied. Re-run with --apply.")


if __name__ == "__main__":
    main()
