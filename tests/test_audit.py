"""Exercise the audit launcher with fake tools, never the developer's Homebrew."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HEAD = "1" * 40
FAKE_TOOL = r'''
import json, os, pathlib, sys
tool = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(json.dumps([tool, *args]) + "\n")
if tool == "git":
    print(os.environ["TAP_HEAD"] if args[0] == "-C" else os.environ["CHECKOUT_HEAD"])
elif args == ["tap"]:
    print("jdylanmc/notch" if os.environ.get("EXISTING_TAP") else "")
elif args == ["--repository", "jdylanmc/notch"]:
    print(os.environ["TAP_PATH"])
elif args[:2] == ["tap", "--custom-remote"]:
    sys.exit(int(os.environ.get("TAP_EXIT", "0")))
elif args[:1] == ["audit"]:
    sys.exit(int(os.environ.get("AUDIT_EXIT", "0")))
else:
    sys.exit(90)
'''


class AuditTests(unittest.TestCase):
    def setUp(self):
        fixture = tempfile.TemporaryDirectory(prefix="tap-audit-tests-")
        self.addCleanup(fixture.cleanup)
        self.root = Path(fixture.name).resolve()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for tool in ("git", "brew"):
            path = self.bin / tool
            path.write_text(f"#!{sys.executable}\n" + FAKE_TOOL)
            path.chmod(0o755)
        self.tap = self.root / "cloned tap"
        for folder in (self.root, self.tap):
            (folder / "Casks").mkdir(parents=True)
            (folder / "Casks/notch-pocket.rb").write_text("synthetic cask, never evaluated")
        self.log = self.root / "calls.jsonl"
        self.env = {
            "PATH": f"{self.bin}:/usr/bin:/bin", "CI": "true", "RUNNER_ENVIRONMENT": "github-hosted",
            "CALL_LOG": str(self.log), "CHECKOUT_HEAD": HEAD, "TAP_HEAD": HEAD, "TAP_PATH": str(self.tap),
        }

    def run_audit(self, **values):
        return subprocess.run(
            ["/bin/bash", str(ROOT / "scripts/audit_cask.sh")], cwd=self.root,
            env={**self.env, **values}, capture_output=True, text=True, timeout=10,
        )

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_audits_qualified_name_only_after_exact_commit_and_content_match(self):
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            ["git", "rev-parse", "HEAD"], ["brew", "tap"],
            ["brew", "tap", "--custom-remote", "jdylanmc/notch", str(self.root)],
            ["brew", "--repository", "jdylanmc/notch"],
            ["git", "-C", str(self.tap), "rev-parse", "HEAD"],
            ["brew", "audit", "--cask", "--strict", "--online", "jdylanmc/notch/notch-pocket"],
        ])

    def test_refuses_local_execution_without_touching_homebrew(self):
        self.assertNotEqual(self.run_audit(CI="false").returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_refuses_existing_tap_without_replacing_it(self):
        self.assertNotEqual(self.run_audit(EXISTING_TAP="1").returncode, 0)
        self.assertEqual(self.calls(), [["git", "rev-parse", "HEAD"], ["brew", "tap"]])

    def test_tap_failure_never_reaches_audit(self):
        self.assertEqual(self.run_audit(TAP_EXIT="17").returncode, 17)
        self.assertFalse(any(call[1] == "audit" for call in self.calls()))

    def test_wrong_commit_or_changed_cask_never_reaches_audit(self):
        self.assertNotEqual(self.run_audit(TAP_HEAD="2" * 40).returncode, 0)
        (self.tap / "Casks/notch-pocket.rb").write_text("different fixture")
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertFalse(any(call[1] == "audit" for call in self.calls()))

    def test_audit_failure_propagates_without_install_or_retry(self):
        self.assertEqual(self.run_audit(AUDIT_EXIT="19").returncode, 19)
        self.assertEqual(sum(call[1] == "audit" for call in self.calls()), 1)
        self.assertFalse(any("install" in call or "untap" in call for call in self.calls()))

    def test_workflow_uses_launcher_without_file_path_audit(self):
        workflow = (ROOT / ".github/workflows/cask.yml").read_text()
        self.assertIn("run: bash scripts/audit_cask.sh", workflow)
        self.assertNotIn('brew audit --cask --strict --online "$PWD/', workflow)


if __name__ == "__main__":
    unittest.main()
