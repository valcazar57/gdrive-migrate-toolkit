#!/usr/bin/env python3
"""Offline fake rclone for the smoke test. Emulates the few subcommands the
toolkit uses, records each invocation, and can inject failures/timeouts. Never
touches any network.

Markers (so we can test behavior without real Drive):
  - path contains "ERRNOTFOUND" -> exit 3 + "directory not found" (path missing)
  - path contains "ERRFAIL"     -> exit 1 + stderr (a real failure)
  - path contains "FILLAFTER"   -> `size` returns 0 on the 1st measurement and 5
                                   afterwards (simulates an empty dest that fills)
  - path contains "TIMEOUT"     -> sleeps (any cmd) so a short --timeout fires
  - `check` path contains "CHKSLOW" -> sleeps only on `check`
  - `check` path contains "CHECKFAIL" -> exit 1 (differences found)
"""
import json
import os
import sys
import time
from pathlib import Path

argv = sys.argv[1:]
joined = " ".join(argv)
log = os.environ.get("GMT_FAKE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(joined + "\n")

cmd = argv[0] if argv else ""

# Slow markers: the caller passes a short --timeout to trigger a real timeout.
if "TIMEOUT" in joined or (cmd == "check" and "CHKSLOW" in joined):
    time.sleep(5)

if cmd in ("size", "lsf", "lsjson", "check"):
    if "ERRFAIL" in joined:
        sys.stderr.write("simulated rclone failure\n")
        sys.exit(1)
    if "ERRNOTFOUND" in joined:
        sys.stderr.write("directory not found\n")
        sys.exit(3)

if cmd == "size":            # size --json PATH
    count = 0
    if "FILLAFTER" in joined:
        seen = 0
        if log and Path(log).exists():
            seen = sum(1 for ln in Path(log).read_text(encoding="utf-8").splitlines()
                       if ln.startswith("size ") and "FILLAFTER" in ln)
        count = 0 if seen <= 1 else 5   # empty before the move, filled after
    print(json.dumps({"count": count, "bytes": count * 1024}))
elif cmd == "lsf":           # files-only listing -> 0 files (moved / empty)
    pass
elif cmd == "lsjson":        # one native (Size -1) + one binary
    print(json.dumps([
        {"Path": "doc1", "Name": "doc1", "Size": -1,
         "MimeType": "application/vnd.google-apps.document"},
        {"Path": "img.png", "Name": "img.png", "Size": 2048, "MimeType": "image/png"},
    ]))
elif cmd == "about":
    print("Total: 30 GiB\nUsed: 18 GiB\nFree: 12 GiB")
elif cmd == "check":
    if "--combined" in argv:                       # write the diff report rclone would
        rp = argv[argv.index("--combined") + 1]
        Path(rp).write_text("* differing/file\n" if "CHECKFAIL" in joined else "= ok\n",
                            encoding="utf-8")
    if "CHECKFAIL" in joined:
        sys.stderr.write("differences found\n")
        sys.exit(1)
# move/copy/mkdir/purge/delete/config/listremotes -> no output, rc 0
sys.exit(0)
