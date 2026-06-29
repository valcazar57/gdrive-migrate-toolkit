#!/usr/bin/env python3
"""verify_counts.py - Compare object count / size between source and dest.

Read-only check that a copy/move added up, WITHOUT touching anything. Compares
per block (`rclone size --json`), never the whole tree recursively at once (that
hangs on large folders - see docs/GOTCHAS.md).

Two modes:
  - Single pair:   --src accountA:Block --dst accountB:Block
  - Pairs table:   --table pairs.csv   (columns: group;source;dest)

Small deficits are almost never data loss: dangling shortcuts (broken links) and
duplicate names that the destination collapses into one. For byte-level certainty
also run `rclone check --one-way SRC DST`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

import common as c


def parse_args():
    ap = argparse.ArgumentParser(description="Compare object count/size source vs dest (read-only).")
    ap.add_argument("--table", default=None, help="';'-delimited CSV group;source;dest")
    ap.add_argument("--src", default=None, help="Single source")
    ap.add_argument("--dst", default=None, help="Single dest")
    ap.add_argument("--src-remote", default=None, help="Default remote for 'source'")
    ap.add_argument("--dst-remote", default=None, help="Default remote for 'dest'")
    ap.add_argument("--out", default=None, help="Output CSV (optional)")
    ap.add_argument("--timeout", type=int, default=1800, help="Timeout per measurement (default 1800)")
    ap.add_argument("--rclone", default=None, help="Path to the rclone binary")
    ap.add_argument("--check", action="store_true",
                    help="Also run `rclone check --one-way SRC DST` (strong: paths + "
                         "sizes/hashes where available). Natives have no hash; see docs/07.")
    return ap.parse_args()


HEADER = ["group", "source", "dest", "n_src", "n_dst", "delta_n", "bytes_src", "bytes_dst", "status"]


def check_pair(rclone, group, src, dst, timeout, check=False):
    def measure(path):
        try:
            return c.rclone_size(rclone, path, timeout=timeout)  # dict, or None if not found
        except c.RcloneError:
            return "error"
    s, d = measure(src), measure(dst)
    ns = s["count"] if isinstance(s, dict) else None
    nd = d["count"] if isinstance(d, dict) else None
    bs = s["bytes"] if isinstance(s, dict) else None
    bd = d["bytes"] if isinstance(d, dict) else None
    delta = ""
    if s == "error":
        status = "source_error"
    elif d == "error":
        status = "dest_error"
    elif s is None:
        status = "source_not_found"
    elif d is None:
        status = "dest_not_found"
    else:
        delta = nd - ns
        if delta == 0:
            status = "ok"
        elif delta > 0:
            status = f"dest_larger(+{delta})"
        else:
            status = f"REVIEW(missing {-delta}: shortcuts/dupe-names?)"
        if check:
            report = "check_" + "".join(ch if ch.isalnum() else "_" for ch in group) + ".txt"
            cargs = (["check", "--one-way", src, dst, "--combined", report]
                     + c.exclude_args(c.DEFAULT_EXCLUDES))
            try:
                rc, _, _ = c.run_rclone(rclone, cargs, timeout=timeout)
            except subprocess.TimeoutExpired:
                rc = 124
            if rc == 0:
                status += "+check_ok"
            else:
                status += f"+REVIEW(check_failed; see {report})"
    print(f"  {group}: src={ns} dst={nd} delta={delta} -> {status}")
    return [group, src, dst, ns, nd, delta, bs, bd, status]


def main():
    a = parse_args()
    rclone = c.find_rclone(a.rclone)

    pairs = []
    if a.table:
        for i, r in enumerate(c.read_table(a.table), 1):
            pairs.append((r.get("group", f"row{i}"),
                          c.qualify(r.get("source", ""), a.src_remote),
                          c.qualify(r.get("dest", ""), a.dst_remote)))
    elif a.src and a.dst:
        pairs.append(("pair", c.qualify(a.src, a.src_remote), c.qualify(a.dst, a.dst_remote)))
    else:
        sys.exit("Provide --table, or both --src and --dst.")

    print(f"Verifying {len(pairs)} pair(s)...")
    rows = [check_pair(rclone, g, s, d, a.timeout, a.check) for g, s, d in pairs]

    if a.out:
        for row in rows:
            c.append_csv(a.out, HEADER, row)
        print(f"Output -> {a.out}")

    bad = [r for r in rows if any(k in str(r[-1]) for k in ("REVIEW", "error", "not_found"))]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} OK." + (f" {len(bad)} to REVIEW." if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
