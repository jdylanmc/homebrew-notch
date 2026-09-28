"""Synthetic cask contracts; no downloads, installations or Homebrew mutations."""

import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_cask", ROOT / "scripts/check_cask.py")
cask = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cask)
DATA = b"synthetic DMG bytes, never installed"
DIGEST = hashlib.sha256(DATA).hexdigest()
SOURCE = f'''cask "notch-pocket" do
  version "0.1.0"
  sha256 "{DIGEST}"

  url "https://github.com/jdylanmc/notch/releases/download/notch-pocket-v#{{version}}/notch-pocket-#{{version}}.dmg"
  name "Notch Pocket"
  desc "Media controls and a file shelf in the macOS notch"
  homepage "https://github.com/jdylanmc/notch"

  depends_on macos: ">= :sonoma"

  app "notch-pocket.app"
end
'''


class CaskTests(unittest.TestCase):
    def test_exact_owned_template_accepts_version_and_checksum(self):
        self.assertEqual(cask.validate(SOURCE), ("0.1.0", DIGEST))

    def test_future_numeric_version_preserves_qualified_download_contract(self):
        self.assertEqual(cask.validate(SOURCE.replace('"0.1.0"', '"0.1.1"')), ("0.1.1", DIGEST))

    def test_quarantine_bypasses_or_additional_ruby_cannot_be_smuggled_in(self):
        for addition in ('system_command "/usr/bin/xattr", args: ["-d", "com.apple.quarantine"]',
                         'auto_updates true', 'sha256 :no_check',
                         'zap trash: "~/Library/Application Support/notchPocket"',
                         'system "echo unexpected"'):
            with self.subTest(addition=addition):
                with self.assertRaises(ValueError):
                    cask.validate(SOURCE.replace("\nend\n", f"\n  {addition}\nend\n"))

    def test_upstream_urls_wrong_product_and_duplicate_fields_are_rejected(self):
        for bad in (
            SOURCE.replace("jdylanmc/notch", "TheBoredTeam/boring.notch"),
            SOURCE.replace("notch-pocket-v#{version}", "v#{version}"),
            SOURCE.replace('app "notch-pocket.app"', 'app "notchPocket.app"'),
            SOURCE.replace('  version "0.1.0"', '  version "0.1.0"\n  version "0.1.1"'),
            SOURCE.replace(DIGEST, "not-a-checksum"),
            SOURCE.replace('"0.1.0"', '"v0.1.0"'),
            SOURCE.replace('"0.1.0"', '"0.01.0"'),
            SOURCE + 'system "unexpected"\n',
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    cask.validate(bad)

    def test_online_check_hashes_exact_download_without_executing_it(self):
        response = io.BytesIO(DATA)
        response.status = 200
        opener = mock.Mock(return_value=response)
        self.assertEqual(cask.verify_download("0.1.0", DIGEST, opener), len(DATA))
        opener.assert_called_once_with(
            "https://github.com/jdylanmc/notch/releases/download/notch-pocket-v0.1.0/notch-pocket-0.1.0.dmg",
            timeout=60,
        )

    def test_empty_wrong_checksum_or_unsuccessful_download_cannot_pass(self):
        for payload, status in ((b"", 200), (b"different", 200), (DATA, 404)):
            with self.subTest(payload=payload, status=status):
                response = io.BytesIO(payload)
                response.status = status
                with self.assertRaises(ValueError):
                    cask.verify_download("0.1.0", DIGEST, mock.Mock(return_value=response))
        with self.assertRaises(HTTPError):
            cask.verify_download("0.1.0", DIGEST, mock.Mock(side_effect=HTTPError(
                "https://github.com", 404, "not published", {}, None)))

    def test_real_casks_when_present_use_the_reviewed_template(self):
        paths = cask.inventory(ROOT)
        self.assertLessEqual(len(paths), 1, "Additional products require explicit policy review.")
        for path in paths:
            self.assertEqual(path.name, "notch-pocket.rb")
            self.assertFalse(path.is_symlink())
            cask.validate(path.read_text(encoding="utf-8"))

    def test_bootstrap_cannot_hide_nested_or_formula_definitions(self):
        for relative in ("Casks/n/notch-pocket.rb", "Casks/other.rb", "Formula/other.rb",
                         "HomebrewFormula/other.rb", "other.rb"):
            for canonical_exists in (False, True):
                with self.subTest(relative=relative, canonical_exists=canonical_exists), \
                        tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    if canonical_exists:
                        (root / "Casks").mkdir()
                        (root / "Casks/notch-pocket.rb").write_text(SOURCE)
                    extra = root / relative
                    extra.parent.mkdir(parents=True, exist_ok=True)
                    extra.write_text(SOURCE)
                    with self.assertRaises(ValueError):
                        cask.inventory(root)

    def test_empty_inventory_is_bootstrap_and_canonical_path_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(cask.inventory(root), [])
            (root / "Casks").mkdir()
            path = root / "Casks/notch-pocket.rb"
            path.write_text(SOURCE)
            self.assertEqual(cask.inventory(root), [path])

    def test_symlinked_cask_directory_is_not_empty_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Casks").symlink_to(root / "elsewhere")
            with self.assertRaises(ValueError):
                cask.inventory(root)


if __name__ == "__main__":
    unittest.main()
