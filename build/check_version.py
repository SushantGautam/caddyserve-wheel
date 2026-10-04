#!/usr/bin/env python3
"""Fail fast if the three version locations disagree.

Checks:
  build/version.txt  ==  pyproject.toml [project] version
                       ==  src/caddyserver/__init__.py __version__
and, when running on a tag push, that the tag is v<version>.

Usage: python build/check_version.py [--tag <tag>]
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    tag = None
    if "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]

    v_file = (REPO / "build" / "version.txt").read_text().strip()
    pyproject = (REPO / "pyproject.toml").read_text()
    init = (REPO / "src" / "caddyserver" / "__init__.py").read_text()

    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject)
    p_version = m.group(1) if m else None
    i = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    i_version = i.group(1) if i else None

    print(f"build/version.txt = {v_file}")
    print(f"pyproject.toml    = {p_version}")
    print(f"__init__.py       = {i_version}")

    if not (v_file and p_version == v_file and i_version == v_file):
        sys.exit("FAIL: version mismatch between build/version.txt, pyproject.toml, __init__.py")

    if tag is not None and tag != f"v{v_file}":
        sys.exit(f"FAIL: tag {tag} does not match build/version.txt ({v_file})")

    # Expose the version to later workflow steps (e.g. the release tag name).
    if (gh_output := os.environ.get("GITHUB_OUTPUT")):
        with open(gh_output, "a") as f:
            f.write(f"v={v_file}\n")

    print(f"version {v_file} consistent")


if __name__ == "__main__":
    main()
