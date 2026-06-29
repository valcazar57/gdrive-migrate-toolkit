#!/usr/bin/env python3
"""detect_natives.py - List Google-native files (Docs/Sheets/Slides) in a path.

Google-native files have NO byte-stream: rclone reports them with Size == -1.
They matter because:
  - move/copy INTRA-account or server-side PRESERVES them (stay native),
  - but going to disk (mirror_account.py) EXPORTS them to Office,
  - and robocopy/cp CANNOT copy them (~197-byte pointer).

Knowing how many there are and where decides a block's strategy (pure binary vs
mixed). Output: stdout + optional CSV.

CAUTION (see docs/GOTCHAS.md): `lsjson -R` recursive over huge folders
(>~2k files) can hang. Use --max-depth to bound it, or measure per block.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys

import common as c


def parse_args():
    ap = argparse.ArgumentParser(description="List Google-native (Size==-1) files in a Drive path.")
    ap.add_argument("--path", required=True, help="Path to inspect (e.g. accountA:Block)")
    ap.add_argument("--max-depth", type=int, default=None, help="Limit depth (avoids hangs on huge trees)")
    ap.add_argument("--out", default=None, help="Output CSV (path;mime)")
    ap.add_argument("--timeout", type=int, default=1800, help="Timeout (default 1800)")
    ap.add_argument("--rclone", default=None, help="Path to the rclone binary")
    return ap.parse_args()


def main():
    a = parse_args()
    rclone = c.find_rclone(a.rclone)

    args = ["lsjson", "-R", "--files-only", a.path]
    if a.max_depth is not None:
        args += ["--max-depth", str(a.max_depth)]
    rc, out, err = c.run_rclone(rclone, args, timeout=a.timeout, capture_to_file=True)
    if rc != 0:
        sys.exit(f"rclone ERROR (rc={rc}): {err.strip()[-500:]}")
    try:
        items = json.loads(out or "[]")
    except json.JSONDecodeError:
        sys.exit("Could not parse lsjson output (tree too big? use --max-depth).")

    natives = [it for it in items if it.get("Size", 0) == -1]
    print(f"{len(natives)} Google-native of {len(items)} files in {a.path}")
    for it in natives[:50]:
        print("  ", it.get("Path", ""))
    if len(natives) > 50:
        print(f"   ... (+{len(natives) - 50} more)")

    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["path", "mime"])
            for it in natives:
                w.writerow([it.get("Path", ""), it.get("MimeType", "")])
        print(f"CSV -> {a.out}")


if __name__ == "__main__":
    main()
