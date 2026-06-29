#!/usr/bin/env python3
"""Offline fake rclone for the smoke test. Emulates the few subcommands the
toolkit uses, records each invocation, and can inject failures. Never touches
any network.

Error injection (so we can test error handling without real Drive):
  - a path containing "ERRNOTFOUND" -> exit 3 + "directory not found" (path missing)
  - a path containing "ERRFAIL"     -> exit 1 + stderr (a real failure)
"""
import json
import os
import sys

argv = sys.argv[1:]
joined = " ".join(argv)
log = os.environ.get("GMT_FAKE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(joined + "\n")

cmd = argv[0] if argv else ""

if cmd in ("size", "lsf", "lsjson"):
    if "ERRFAIL" in joined:
        sys.stderr.write("simulated rclone failure\n")
        sys.exit(1)
    if "ERRNOTFOUND" in joined:
        sys.stderr.write("directory not found\n")
        sys.exit(3)

if cmd == "size":            # size --json PATH
    print(json.dumps({"count": 3, "bytes": 3072}))
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
# move/copy/mkdir/purge/delete/check/config/listremotes -> no output, rc 0
sys.exit(0)
