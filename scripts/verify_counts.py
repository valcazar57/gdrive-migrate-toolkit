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
    return ap.parse_args()


HEADER = ["group", "source", "dest", "n_src", "n_dst", "delta_n", "bytes_src", "bytes_dst", "status"]


def check_pair(rclone, group, src, dst, timeout):
    s = c.rclone_size(rclone, src, timeout=timeout)
    d = c.rclone_size(rclone, dst, timeout=timeout)
    ns, nd = (s["count"] if s else None), (d["count"] if d else None)
    bs, bd = (s["bytes"] if s else None), (d["bytes"] if d else None)
    if ns is None:
        status, delta = "source_unreachable", ""
    elif nd is None:
        status, delta = "dest_unreachable", ""
    else:
        delta = nd - ns
        if delta == 0:
            status = "ok"
        elif delta > 0:
            status = f"dest_larger(+{delta})"
        else:
            status = f"REVIEW(missing {-delta}: shortcuts/dupe-names?)"
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
    rows = [check_pair(rclone, g, s, d, a.timeout) for g, s, d in pairs]

    if a.out:
        for row in rows:
            c.append_csv(a.out, HEADER, row)
        print(f"Output -> {a.out}")

    bad = [r for r in rows if str(r[-1]).startswith("REVIEW") or "unreachable" in str(r[-1])]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} OK." + (f" {len(bad)} to REVIEW." if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
