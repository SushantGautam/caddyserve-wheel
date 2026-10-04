#!/usr/bin/env python3
"""Pre-push local gate: validate dist/ the way PyPI will.

Runs the checks whose failures were seen in CI:
  1. twine check          (metadata structure: PKG-INFO, body, ...)
  2. trove classifiers    (PyPI 400s on invalid classifier values)
  3. core metadata parse  (all wheels + sdist parse as PEP 643 metadata)

Usage: python build/check_dist.py        (expects dist/ to exist)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import tarfile
import zipfile

DIST = Path(__file__).resolve().parent.parent / "dist"
TROVE_LIST = Path("/tmp/trove-list.txt")  # optional cache; fetched below if missing


def trove_valid() -> set[str]:
    if TROVE_LIST.exists():
        return {l.strip() for l in TROVE_LIST.read_text().splitlines() if l.strip()}
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        venv = Path(td) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                       capture_output=True)
        subprocess.run([str(venv / "bin" / "pip"), "install", "-q",
                        "trove-classifiers"], check=True, capture_output=True)
        out = subprocess.run([str(venv / "bin" / "trove-classifiers"), "list"],
                             check=True, capture_output=True, text=True)
    return {l.strip() for l in out.stdout.splitlines() if l.strip()}


def read_metadata_bytes(artifact: Path) -> bytes:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as zf:
            meta = [n for n in zf.namelist()
                    if n.endswith(".dist-info/METADATA")]
            return zf.read(meta[0])
    with tarfile.open(artifact) as tf:
        pkg = [m for m in tf.getmembers() if m.name.endswith("PKG-INFO")]
        if not pkg:
            raise ValueError(f"{artifact.name}: no PKG-INFO in sdist")
        return tf.extractfile(pkg[0]).read()


def main() -> int:
    if not DIST.exists():
        print("dist/ missing — run `python build/wheels.py` first", file=sys.stderr)
        return 2
    artifacts = sorted(list(DIST.glob("*.whl")) + list(DIST.glob("*.tar.gz")))
    if not artifacts:
        print("no wheels/sdist in dist/", file=sys.stderr)
        return 2

    print(f"== 1/3 twine check ({len(artifacts)} artifacts)")
    import shutil
    twine = shutil.which("twine")
    if twine is None:
        print("  SKIP (twine not on PATH) — install: pip install twine")
    else:
        import subprocess
        r = subprocess.run([twine, "check", *[str(a) for a in artifacts]],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0:
            print("FAIL: twine check")
            return 1
        if "PASSED" not in r.stdout:
            print("FAIL: twine check did not report PASSED")
            return 1

    print("== 2/3 trove classifiers")
    valid = trove_valid()
    print(f"  {len(valid)} valid classifiers loaded")
    bad = []
    for a in artifacts:
        meta = read_metadata_bytes(a).decode()
        for m in re.finditer(r"^Classifier: (.+)$", meta, re.M):
            if m.group(1).strip() not in valid:
                bad.append((a.name, m.group(1).strip()))
    if bad:
        for name, cls in bad:
            print(f"  BAD {name}: {cls!r}  -> PyPI returns 400 on upload")
        print("FAIL: invalid classifier(s)")
        return 1
    print("  all classifiers valid")

    print("== 3/3 core metadata parse")
    from email.parser import Parser
    for a in artifacts:
        meta = read_metadata_bytes(a).decode()
        body = meta.split("\n\n", 1)
        parsed = Parser().parsestr(body[0] + "\n")
        name, ver = parsed.get("Name"), parsed.get("Version")
        if not name or not ver:
            print(f"  BAD {a.name}: missing Name/Version")
            return 1
        print(f"  OK  {a.name}  ({name} {ver}, body {len(body[1]) if len(body) > 1 else 0} chars)")

    print("\nAll local checks passed — safe to push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
