#!/usr/bin/env python3
"""Validate an existing build before publishing its artifact as a release."""

import json
import os
from pathlib import Path
import re
import subprocess


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["RUN_ID"]
    if not run_id.isdecimal():
        raise SystemExit("run_id must be numeric")
    run = api(f"repos/{repo}/actions/runs/{run_id}")
    if not (
        run["status"] == "completed"
        and run["conclusion"] == "success"
        and run["event"] == "workflow_dispatch"
        and run["head_branch"] == "main"
        and run["path"] == ".github/workflows/build.yml"
        and run["head_repository"]["full_name"] == repo
    ):
        raise SystemExit("Expected a successful manual Build run from this repository's main branch")
    sha = run["head_sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit("Unexpected build commit")
    # A run may override the pin; name the release by its build run, not a
    # guessed browser version. The release target identifies the exact recipe.
    tag = f"build-{run_id}"
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"sha={sha}\ntag={tag}\n")
    print(f"Verified build {run_id} at {sha}; release {tag}")


if __name__ == "__main__":
    main()
