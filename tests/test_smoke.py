#!/usr/bin/env python3
"""Offline smoke tests for gdrive-migrate-toolkit. No network, no real rclone.

Builds an OS-appropriate launcher so the scripts call tests/fake_rclone.py instead
of the real rclone, then asserts the scripts produce the right command lines, logs,
error handling and exit codes in dry-run and apply modes.
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
        self.table = self.write_table(
            "Sales;00 - INBOX/Sales;Sales and Marketing;D:/MIRROR/Sales\n")
        self.env = dict(os.environ, RCLONE=str(self.launcher), GMT_FAKE_LOG=str(self.log))

    def tearDown(self):
        self.tmp.cleanup()

    def write_table(self, body, name="move_table.csv"):
        p = self.d / name
        p.write_text("group;source;dest;mirror\n" + body, encoding="utf-8")
        return p

    def run_script(self, name, *args):
        cmd = [sys.executable, str(SCRIPTS / name), *args]
        return subprocess.run(cmd, cwd=self.d, env=self.env, capture_output=True, text=True)

    # ---- reorg_move ----
    def test_reorg_dryrun_then_apply(self):
        r = self.run_script("reorg_move.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountA:")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DRY-RUN", r.stdout)
        r = self.run_script("reorg_move.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountA:", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("source_left=0", r.stdout)
        log = self.log.read_text(encoding="utf-8")
        self.assertRegex(log, r"(?m)^move ")
        self.assertNotIn("--server-side-across-configs", log)   # intra-account: no cross-config

    def test_reorg_skips_missing_source(self):
        table = self.write_table("Gone;ERRNOTFOUND/x;Dest;\n", "missing.csv")
        r = self.run_script("reorg_move.py", "--table", str(table),
                            "--src-remote", "accountA:", "--dst-remote", "accountA:", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)            # missing source = clean skip
        self.assertIn("SKIP", r.stdout)
        self.assertNotIn("ERROR", r.stdout)

    def test_reorg_errors_on_unreadable_source(self):
        table = self.write_table("Bad;ERRFAIL/x;Dest;\n", "bad.csv")
        r = self.run_script("reorg_move.py", "--table", str(table),
                            "--src-remote", "accountA:", "--dst-remote", "accountA:", "--apply")
        self.assertEqual(r.returncode, 1)                      # access error must fail, not skip
        self.assertIn("ERROR", r.stdout)

    def test_reorg_review_exits_nonzero(self):
        # dest fills to 5 objects but source reported 0 -> added != src -> REVIEW
        table = self.write_table("Mism;00 - INBOX/Sales;FILLAFTER;\n", "mism.csv")
        r = self.run_script("reorg_move.py", "--table", str(table),
                            "--src-remote", "accountA:", "--dst-remote", "accountA:", "--apply")
        self.assertEqual(r.returncode, 2)                      # REVIEW -> exit 2 (not silent ok)
        self.assertIn("REVIEW(added", r.stdout)

    def test_reorg_blocks_cross_account_by_default(self):
        table = self.write_table("X;Block;Inbox/Block;\n", "cross.csv")
        r = self.run_script("reorg_move.py", "--table", str(table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:", "--apply")
        self.assertEqual(r.returncode, 1)                      # cross-account move blocked
        self.assertIn("BLOCKED", r.stdout)

    def test_reorg_allows_cross_account_with_flag(self):
        table = self.write_table("X;Block;Inbox/Block;\n", "cross2.csv")
        r = self.run_script("reorg_move.py", "--table", str(table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:",
                            "--allow-cross-account-move", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--server-side-across-configs", self.log.read_text(encoding="utf-8"))

    # ---- evacuate ----
    def test_evacuate_two_passes(self):
        r = self.run_script("evacuate.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("--server-side-across-configs", log)             # pass 1 (modern flag)
        self.assertNotIn("--drive-server-side-across-configs", log)    # not the deprecated one
        self.assertIn("--ignore-existing", log)                       # pass 2

    # ---- detect_natives ----
    def test_detect_natives(self):
        r = self.run_script("detect_natives.py", "--path", "accountA:Block")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 Google-native", r.stdout)

    # ---- verify_counts ----
    def test_verify_counts_ok(self):
        r = self.run_script("verify_counts.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK", r.stdout)

    def test_verify_counts_flags_error(self):
        table = self.write_table("Bad;ERRFAIL/x;ERRFAIL/y;\n", "verr.csv")
        r = self.run_script("verify_counts.py", "--table", str(table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:")
        self.assertEqual(r.returncode, 1)
        self.assertIn("error", r.stdout)

    def test_verify_check_ok(self):
        r = self.run_script("verify_counts.py", "--table", str(self.table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:", "--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("check_ok", r.stdout)
        self.assertRegex(self.log.read_text(encoding="utf-8"), r"(?m)^check --one-way ")
        self.assertTrue((self.d / "check_Sales.txt").exists())   # --combined report written

    def test_verify_check_failure(self):
        table = self.write_table("Bad;CHECKFAIL/a;CHECKFAIL/b;\n", "vchk.csv")
        r = self.run_script("verify_counts.py", "--table", str(table),
                            "--src-remote", "accountA:", "--dst-remote", "accountB:", "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("check_failed", r.stdout)

    # ---- timeout handling (short --timeout vs a slow fake) ----
    def test_reorg_size_timeout_exits_nonzero(self):
        table = self.write_table("Slow;TIMEOUT/x;Dest;\n", "rto.csv")
        r = self.run_script("reorg_move.py", "--table", str(table), "--timeout", "1",
                            "--src-remote", "accountA:", "--dst-remote", "accountA:", "--apply")
        self.assertEqual(r.returncode, 1)            # measurement timeout -> error, not skip
        self.assertIn("ERROR", r.stdout)

    def test_evacuate_copy_timeout_review(self):
        table = self.write_table("Slow;TIMEOUT/x;Dest;\n", "eto.csv")
        r = self.run_script("evacuate.py", "--table", str(table), "--timeout", "1",
                            "--src-remote", "accountA:", "--dst-remote", "accountB:",
                            "--pass", "1", "--apply")
        self.assertEqual(r.returncode, 2)            # copy timeout -> REVIEW, not silent ok
        self.assertIn("review=1", r.stdout)          # copy timeout -> REVIEW, not silent ok

    def test_verify_check_timeout_fails(self):
        table = self.write_table("Slow;CHKSLOW/a;CHKSLOW/b;\n", "vto.csv")
        r = self.run_script("verify_counts.py", "--table", str(table), "--timeout", "1",
                            "--src-remote", "accountA:", "--dst-remote", "accountB:", "--check")
        self.assertEqual(r.returncode, 1)            # check timeout -> REVIEW
        self.assertIn("check_failed", r.stdout)

    # ---- mirror ----
    def test_mirror_exports_natives_flag(self):
        r = self.run_script("mirror_account.py", "--remote", "accountA:",
                            "--dest", str(self.d / "mir"), "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--drive-export-formats", self.log.read_text(encoding="utf-8"))

    # ---- schema stays in sync with the scripts ----
    def test_schema_matches_headers(self):
        schema = (ROOT / "templates" / "changes.schema.csv").read_text(encoding="utf-8")
        self.assertIn(";".join(reorg_move.HEADER), schema)
        self.assertIn(";".join(evacuate.HEADER), schema)


if __name__ == "__main__":
    unittest.main()
