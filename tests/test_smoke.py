#!/usr/bin/env python3
"""Offline smoke tests for gdrive-migrate-toolkit. No network, no real rclone.

Builds an OS-appropriate launcher so the scripts call tests/fake_rclone.py instead
of the real rclone, then asserts the scripts produce the right command lines, logs
and exit codes in dry-run and apply modes.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
FAKE = Path(__file__).resolve().parent / "fake_rclone.py"

sys.path.insert(0, str(SCRIPTS))
import reorg_move  # noqa: E402  (import sanity + HEADER access)
import evacuate    # noqa: E402


def make_launcher(d: Path) -> Path:
    """Create an executable that runs the fake rclone with the current Python."""
    if os.name == "nt":
        p = d / "rclone.bat"
        p.write_text(f'@echo off\r\n"{sys.executable}" "{FAKE}" %*\r\n', encoding="utf-8")
    else:
        p = d / "rclone"
        p.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n', encoding="utf-8")
        p.chmod(0o755)
    return p


class Smoke(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.launcher = make_launcher(self.d)
        self.log = self.d / "fake.log"
        self.table = self.d / "move_table.csv"
        self.table.write_text(
            "group;source;dest;mirror\n"
            "Sales;00 - INBOX/Sales;Sales and Marketing;D:/MIRROR/Sales\n",
            encoding="utf-8")
        self.env = dict(os.environ, RCLONE=str(self.launcher), GMT_FAKE_LOG=str(self.log))

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, name, *args):
        cmd = [sys.executable, str(SCRIPTS / name), *args]
        return subprocess.run(cmd, cwd=self.d, env=self.env, capture_output=True, text=True)

    def test_reorg_dryrun_then_apply(self):
        r = self.run_script("reorg_move.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountA:")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DRY-RUN", r.stdout)
        r = self.run_script("reorg_move.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountA:", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("-> ok", r.stdout)
        log = self.log.read_text(encoding="utf-8")
        self.assertRegex(log, r"(?m)^move ")                       # reorg uses move
        self.assertNotIn("--drive-server-side-across-configs", log)  # intra-account

    def test_evacuate_two_passes(self):
        r = self.run_script("evacuate.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("--drive-server-side-across-configs", log)  # pass 1
        self.assertIn("--ignore-existing", log)                   # pass 2

    def test_detect_natives(self):
        r = self.run_script("detect_natives.py", "--path", "accountA:Block")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 Google-native", r.stdout)

    def test_verify_counts_ok(self):
        r = self.run_script("verify_counts.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK", r.stdout)

    def test_mirror_exports_natives_flag(self):
        r = self.run_script("mirror_account.py", "--remote", "accountA:",
                            "--dest", str(self.d / "mir"), "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--drive-export-formats", self.log.read_text(encoding="utf-8"))

    def test_schema_matches_headers(self):
        schema = (ROOT / "templates" / "changes.schema.csv").read_text(encoding="utf-8")
        self.assertIn(";".join(reorg_move.HEADER), schema)
        self.assertIn(";".join(evacuate.HEADER), schema)


if __name__ == "__main__":
    unittest.main()
