"""Shared helpers for gdrive-migrate-toolkit.

Design notes (see README / docs/GOTCHAS.md):
- Nothing hardcoded: the rclone binary is resolved via --rclone, $RCLONE or PATH.
- rclone is ALWAYS invoked with args as a LIST (no shell): safe with paths that
  contain '|', accents, parentheses or trailing spaces.
- Large listings are redirected to a temp file and re-read, because on the
  Windows Python in this kind of environment subprocess can return stdout=None
  for large outputs.
- Functions are idempotent: a missing folder returns None instead of crashing.

No external dependencies. Python 3.8+.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Standard flags for move/copy. Conservative with Drive's rate limit.
STD_FLAGS = [
    "--transfers", "8",
    "--tpslimit", "10",
    "--drive-pacer-min-sleep", "10ms",
]

DEFAULT_EXCLUDES = ["desktop.ini"]


def find_rclone(explicit: str | None = None) -> str:
    """Resolve the rclone binary: --rclone > $RCLONE > PATH."""
    cand = explicit or os.environ.get("RCLONE") or "rclone"
    found = shutil.which(cand)
    if not found and Path(cand).exists():
        found = str(Path(cand).resolve())
    if not found:
        sys.exit(
            "ERROR: 'rclone' not found. Install it, pass it with --rclone PATH, "
            "or export the RCLONE variable. See docs/01-setup-rclone.md"
        )
    return found


def exclude_args(excludes) -> list:
    args = []
    for ex in (excludes or []):
        args += ["--exclude", ex]
    return args


def run_rclone(rclone: str, args, *, timeout=None, capture_to_file=False):
    """Run rclone with args (list). Returns (returncode, stdout, stderr).

    capture_to_file=True redirects stdout to a temp file and re-reads it (avoids
    the stdout=None bug for large outputs on Windows).
    """
    cmd = [rclone] + [str(a) for a in args]
    if capture_to_file:
        fd, tmp = tempfile.mkstemp(suffix=".rclone.out")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                p = subprocess.run(
                    cmd, stdout=fh, stderr=subprocess.PIPE,
                    timeout=timeout, text=True, encoding="utf-8",
                )
            out = Path(tmp).read_text(encoding="utf-8", errors="replace")
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return p.returncode, out, (p.stderr or "")
    p = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout, text=True, encoding="utf-8",
    )
    return p.returncode, (p.stdout or ""), (p.stderr or "")


class RcloneError(RuntimeError):
    """rclone failed for a reason other than 'path does not exist'."""


def _not_found(rc, err):
    """True when rclone failed only because the path does not exist."""
    return rc == 3 or "directory not found" in (err or "").lower()


def rclone_size(rclone: str, path: str, *, excludes=DEFAULT_EXCLUDES, timeout=1800):
    """Return {'count': int, 'bytes': int}, or None if the path does not exist.

    Raises RcloneError on a real failure (timeout, auth, 429, network, bad JSON)
    so callers never mistake an access error for an empty / already-moved folder.
    'count' includes Google-native files (they count as an object at 0 bytes).
    """
    args = ["size", "--json", path] + exclude_args(excludes)
    try:
        rc, out, err = run_rclone(rclone, args, timeout=timeout, capture_to_file=True)
    except subprocess.TimeoutExpired:
        raise RcloneError(f"rclone size timed out after {timeout}s for {path}")
    if rc != 0:
        if _not_found(rc, err):
            return None
        raise RcloneError(f"rclone size failed (rc={rc}) for {path}: {err.strip()[-300:]}")
    try:
        d = json.loads(out.strip() or "{}")
    except json.JSONDecodeError:
        raise RcloneError(f"rclone size returned invalid JSON for {path}")
    return {"count": int(d.get("count", 0)), "bytes": int(d.get("bytes", 0))}


def rclone_count_files(rclone: str, path: str, *, excludes=DEFAULT_EXCLUDES, timeout=1800):
    """Count real files with `lsf -R --files-only`.

    Returns the count, or None if the path does not exist. Raises RcloneError on
    a real failure. Used for the 'everything moved' check (source = 0 after move).
    """
    args = ["lsf", "-R", "--files-only", path] + exclude_args(excludes)
    try:
        rc, out, err = run_rclone(rclone, args, timeout=timeout, capture_to_file=True)
    except subprocess.TimeoutExpired:
        raise RcloneError(f"rclone lsf timed out after {timeout}s for {path}")
    if rc != 0:
        if _not_found(rc, err):
            return None
        raise RcloneError(f"rclone lsf failed (rc={rc}) for {path}: {err.strip()[-300:]}")
    return sum(1 for line in out.splitlines() if line.strip())


def rclone_size_or_none(rclone, path, **kw):
    """rclone_size for display-only callers: returns None on any error too."""
    try:
        return rclone_size(rclone, path, **kw)
    except RcloneError:
        return None


def remote_of(path: str) -> str:
    """The 'remote' part of 'remote:path' (or '' if the cell has no remote)."""
    return path.split(":", 1)[0] if ":" in path else ""


def append_csv(path, header, row):
    """Append a row to a ';'-delimited CSV. Writes the header if the file is new."""
    p = Path(path)
    new = not p.exists()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        if new:
            w.writerow(header)
        w.writerow(row)


def read_table(path):
    """Read a ';'-delimited CSV with header into a list of dicts. Skips blank
    rows and comments starting with '#'."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for r in reader:
            if not r:
                continue
            first = (next(iter(r.values())) or "").strip()
            if not first or first.startswith("#"):
                continue
            rows.append({(k or "").strip(): (v or "").strip() for k, v in r.items()})
    return rows


def qualify(cell: str, remote: str | None) -> str:
    """Prepend 'remote:' to a path cell when it has no remote of its own.

    rclone remote detection = 'name:...' with name having no '/' or '\\'. A local
    Windows path ('D:/x') also has ':', so we only prepend when the cell's first
    segment has NO ':'.
    """
    cell = cell.strip()
    if not remote:
        return cell
    head = cell.split("/", 1)[0].split("\\", 1)[0]
    if ":" in head:
        return cell  # already qualified (remote: or local drive)
    sep = "" if remote.endswith(":") else ":"
    return f"{remote}{sep}{cell}"


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return datetime.now().strftime("%Y%m%d")


def human(n: int) -> str:
    f = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(f) < 1024.0:
            return f"{f:.1f} {unit}"
        f /= 1024.0
    return f"{f:.1f} PiB"


def banner(apply: bool):
    mode = "APPLY (real changes)" if apply else "DRY-RUN (simulation, no changes)"
    print(f"=== gdrive-migrate-toolkit - mode: {mode} ===")
    if not apply:
        print("    (add --apply to actually run)")
