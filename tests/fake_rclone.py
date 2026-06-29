#!/usr/bin/env python3
"""Offline fake rclone for the smoke test. Emulates the few subcommands the
toolkit uses and records each invocation. Never contacts any network."""
import json
import os
import sys

argv = sys.argv[1:]
log = os.environ.get("GMT_FAKE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(" ".join(argv) + "\n")

cmd = argv[0] if argv else ""
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
