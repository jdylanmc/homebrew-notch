#!/usr/bin/env python3
"""Validate the owned Notch Pocket cask without installing or executing it."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
URL_TEMPLATE = ("https://github.com/jdylanmc/notch/releases/download/"
                "notch-pocket-v#{version}/notch-pocket-#{version}.dmg")
TEMPLATE = '''cask "notch-pocket" do
  version "{version}"
  sha256 "{sha256}"

  url "{url}"
  name "Notch Pocket"
  desc "Media controls and a file shelf in the macOS notch"
  homepage "https://github.com/jdylanmc/notch"

  depends_on macos: ">= :sonoma"

  app "notch-pocket.app"
end
'''


def inventory(root):
    def read_error(error):
        raise error

    casks = []
    for directory, folders, files in os.walk(root, followlinks=False, onerror=read_error):
        if Path(directory) == root and ".git" in folders:
            folders.remove(".git")
        for name in folders + files:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError("Symlinks are not supported in the owned tap.")
            if path.suffix == ".rb":
                if path.relative_to(root) != Path("Casks/notch-pocket.rb"):
                    raise ValueError("Unexpected Ruby definition; this tap supports only Casks/notch-pocket.rb.")
                casks.append(path)
    return casks


def validate(source):
    versions = re.findall(r'^  version "((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"$',
                          source, re.MULTILINE)
    hashes = re.findall(r'^  sha256 "([0-9a-f]{64})"$', source, re.MULTILINE)
    if len(versions) != 1 or len(hashes) != 1:
        raise ValueError("Expected one numeric release version and one SHA-256.")
    version, digest = versions[0], hashes[0]
    if source != TEMPLATE.format(version=version, sha256=digest, url=URL_TEMPLATE):
        raise ValueError("Cask differs from the reviewed product template; review policy changes explicitly.")
    return version, digest


def verify_download(version, expected, opener=urlopen):
    url = URL_TEMPLATE.replace("#{version}", version)
    digest = hashlib.sha256()
    size = 0
    with opener(url, timeout=60) as response:
        if response.status != 200:
            raise ValueError("Release download did not return HTTP 200.")
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
            size += len(block)
    if size == 0 or digest.hexdigest() != expected:
        raise ValueError("Published DMG does not match the cask's SHA-256.")
    return size


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="Download and hash the public DMG; never install it")
    args = parser.parse_args(argv)
    try:
        inventory(ROOT)
        path = ROOT / "Casks/notch-pocket.rb"
        if path.is_symlink():
            raise ValueError("Cask must be a regular tracked file, not a symlink.")
        version, digest = validate(path.read_text(encoding="utf-8"))
        if args.online:
            size = verify_download(version, digest)
            print(f"Verified published Notch Pocket {version}: {size} bytes, SHA-256 {digest}")
        else:
            print(f"Validated Notch Pocket {version} cask structure; download not checked.")
    except (OSError, ValueError, URLError) as exc:
        print(f"Cask validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
