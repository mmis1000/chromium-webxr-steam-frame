#!/usr/bin/env python3
"""Check the patch series against a Chromium release without a full checkout."""

import argparse
import base64
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request


def main():
    repo = Path(__file__).resolve().parents[1]
    pinned = re.search(
        r"^CHROMIUM_VERSION=\$\{CHROMIUM_VERSION:-(.+)\}$",
        (repo / "build/build.sh").read_text(),
        re.MULTILINE,
    ).group(1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", default=pinned)
    args = parser.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", args.version):
        parser.error("version must be a four-part Chromium release number")

    patches = sorted((repo / "patches").glob("*.patch"))
    files = set()
    for patch in patches:
        files.update(re.findall(r"^--- a/(.+)$", patch.read_text(), re.MULTILINE))

    with tempfile.TemporaryDirectory(prefix="chromium-patches-") as directory:
        tree = Path(directory)
        subprocess.run(["git", "init", "-q", directory], check=True)
        for name in sorted(files):
            url = (
                "https://chromium.googlesource.com/chromium/src/+/refs/tags/"
                f"{args.version}/{name}?format=TEXT"
            )
            with urllib.request.urlopen(url, timeout=60) as response:
                data = base64.b64decode(response.read(), validate=True)
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        for patch in patches:
            subprocess.run(["git", "apply", "--check", str(patch)], cwd=tree, check=True)
            subprocess.run(["git", "apply", str(patch)], cwd=tree, check=True)
            # prepare() uses this check to skip patches on a repeated run.
            subprocess.run(
                ["git", "apply", "--reverse", "--check", str(patch)],
                cwd=tree,
                check=True,
            )
            print(f"{patch.name}: applies and reverse-checks on {args.version}", flush=True)


if __name__ == "__main__":
    main()
