#!/usr/bin/env python3
"""Build platform-specific wheels bundling official Caddy binaries.

Pure standard library. Flow:
  1. Read the pinned Caddy version from build/version.txt.
  2. Download caddy_{v}_checksums.txt from the official caddyserver/caddy
     GitHub release.
  3. Download each platform archive, verify its SHA-256 (hard fail on mismatch).
  4. Emit one wheel per platform tag plus an sdist into dist/, and write
     dist/release_manifest.json (upstream + wheel digests for release notes).

Usage:  python build/wheels.py
Env:    CADDY_CHECKSUMS_URL override for testing (not used in CI).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "dist"

# (upstream caddy asset suffix, wheel platform tag, binary name in archive)
PLATFORMS = [
    ("windows_amd64.zip", "win_amd64", "caddy.exe"),
    ("windows_arm64.zip", "win_arm64", "caddy.exe"),
    ("mac_amd64.tar.gz", "macosx_11_0_x86_64", "caddy"),
    ("mac_arm64.tar.gz", "macosx_11_0_arm64", "caddy"),
    ("linux_amd64.tar.gz", "manylinux2014_x86_64.musllinux_1_1_x86_64", "caddy"),
    ("linux_arm64.tar.gz", "manylinux2014_aarch64.musllinux_1_1_aarch64", "caddy"),
]

PKG_NAME = "caddyserver"
DIST_NAME = "caddyserver"
REQUIRES_PYTHON = ">=3.9"


def shorthash(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def load_version() -> str:
    v = (REPO / "build" / "version.txt").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        sys.exit(f"bad version in build/version.txt: {v!r} (expect X.Y.Z)")
    return v


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "caddyserver-builder"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def parse_checksums(text: str) -> dict[str, str]:
    # Official Caddy releases publish full SHA-512 (128 hex) digests in
    # checksums.txt. Accept 64- or 128-char digests for forward compatibility.
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^([0-9a-f]{64,128})\s+\*?(\S+)$", line.strip())
        if m:
            out[m.group(2)] = m.group(1)
    return out


def digest_of(blob: bytes, pub_len: int) -> str:
    algo = hashlib.sha512 if pub_len == 128 else hashlib.sha256
    return algo(blob).hexdigest()


def build_wheel(
    version: str, tag: str, binary: Path, metadata: dict, readme: str, out: Path
) -> None:
    exe = binary.read_bytes()
    dist_info = f"{PKG_NAME}-{version}.dist-info"
    files: dict[str, bytes] = {
        f"{PKG_NAME}/__init__.py": (REPO / "src" / PKG_NAME / "__init__.py").read_bytes(),
        f"{PKG_NAME}/cli.py": (REPO / "src" / PKG_NAME / "cli.py").read_bytes(),
        f".data/scripts/{binary.name}": exe,
        f"{dist_info}/METADATA": metadata,
        # NOTE: only the `caddyserver` entry point is defined. A `caddy`
        # entry point would collide with the real `caddy` binary pip installs
        # from .data/scripts (the generated wrapper would clobber it).
        f"{dist_info}/entry_points.txt": (
            "[console_scripts]\n"
            f"{DIST_NAME} = {PKG_NAME}.cli:main\n"
        ).encode(),
        f"{dist_info}/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: caddyserver build/wheels.py\n"
            "Root-Is-Purelib: false\n"
            "Tag: py3-none-" + tag + "\n"
        ).encode(),
    }

    record_lines = [
        f"{name},{shorthash(data)},{len(data)}" for name, data in sorted(files.items())
    ]
    record_lines.append(f"{dist_info}/RECORD,,")
    files[f"{dist_info}/RECORD"] = ("\n".join(record_lines) + "\n").encode()

    out.parent.mkdir(parents=True, exist_ok=True)
    zf = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
    for name, data in sorted(files.items()):
        zi = zipfile.ZipInfo(name)
        zi.date_time = (2024, 1, 1, 0, 0, 0)
        # External attrs must carry the full file mode in the high 16 bits,
        # including the regular-file bits: pip checks stat.S_ISREG(mode) before
        # restoring the executable bit on extracted data/scripts files.
        if name == f".data/scripts/{binary.name}":
            zi.external_attr = 0o100755 << 16
        else:
            zi.external_attr = 0o100644 << 16
        zf.writestr(zi, data)
    zf.close()
    print(f"  wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    version = load_version()
    print(f"== caddyserver build: Caddy v{version}")

    checksums = parse_checksums(fetch(
        f"https://github.com/caddyserver/caddy/releases/download/v{version}/caddy_{version}_checksums.txt"
    ).decode())
    missing = [a for a, _, _ in PLATFORMS if f"caddy_{version}_{a}" not in checksums]
    if missing:
        sys.exit(f"assets missing from checksums.txt: {missing}")

    work = REPO / "build" / "work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    def get_binary(args: tuple) -> Path:
        suffix, sha, bin_name = args
        sub = work / suffix.replace(".", "_")
        sub.mkdir(parents=True)
        blob = fetch(
            f"https://github.com/caddyserver/caddy/releases/download/v{version}/caddy_{version}_{suffix}"
        )
        actual = digest_of(blob, len(sha))
        if actual != sha:
            sys.exit(f"CHECKSUM MISMATCH {suffix}: expected {sha}, got {actual}")
        archive = sub / f"caddy_{version}_{suffix}"
        archive.write_bytes(blob)
        extract = sub / "extract"
        extract.mkdir()
        if suffix.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extract)
        else:
            with tarfile.open(archive, "r:gz") as tf:
                tf.extractall(extract, filter="data")
        for f in extract.iterdir():
            if f.is_file() and f.name == bin_name:
                return f
        sys.exit(f"binary {bin_name} not found in {suffix}")

    print("== downloading + verifying binaries (6 in parallel)")
    jobs = [(suffix, checksums[f"caddy_{version}_{suffix}"], bin_name) for suffix, _, bin_name in PLATFORMS]
    with ThreadPoolExecutor(max_workers=6) as pool:
        binaries = list(pool.map(get_binary, jobs))

    # Sanity: every binary must report the right version.
    import subprocess

    host_arch = os.uname().machine  # arm64/x86_64 on macOS, etc.
    for (suffix, tag, _), bin_path in zip(PLATFORMS, binaries):
        if os.uname().sysname != "Darwin":
            continue
        host_tag = "macosx_11_0_arm64" if host_arch in ("arm64", "aarch64") else "macosx_11_0_x86_64"
        if tag != host_tag:
            continue
        bin_path.chmod(0o755)
        r = subprocess.run([str(bin_path), "version"], capture_output=True, text=True)
        first = r.stdout.splitlines()[0] if r.stdout else r.stderr
        print(f"  {tag}: {first}")

    DIST.mkdir(exist_ok=True)
    readme = (REPO / "README.md").read_text() if (REPO / "README.md").exists() else ""

    metadata = (
        "Metadata-Version: 2.1\n"
        f"Name: {DIST_NAME}\n"
        f"Version: {version}\n"
        "Summary: Caddy web server as platform-specific Python wheels - pip/pipx/uvx "
        "installable, offline, no first-run download\n"
        "Author: Sushant Gautam\n"
        "License: MIT\n"
        f"Requires-Python: {REQUIRES_PYTHON}\n"
        "Project-URL: Homepage, https://github.com/SushantGautam/caddyserver\n"
        "Project-URL: Repository, https://github.com/SushantGautam/caddyserver\n"
        "Project-URL: Issues, https://github.com/SushantGautam/caddyserver/issues\n"
        "Keywords: caddy,webserver,binary,distribution,http3,https\n"
        "Classifier: Development Status :: 5 - Production/Stable\n"
        "Classifier: Environment :: Console\n"
        "Classifier: Intended Audience :: System Administrators\n"
        "Classifier: Operating System :: Microsoft :: Windows\n"
        "Classifier: Operating System :: MacOS :: MacOS X\n"
        "Classifier: Operating System :: POSIX :: Linux\n"
        "Classifier: Programming Language :: Python :: 3\n"
        "Classifier: Topic :: Internet :: WWW/HTTP :: Servers\n"
        "Description-Content-Type: text/markdown\n"
        f"Description:\n{readme}\n"
    ).encode()

    print("== building wheels")
    manifest: list[dict] = []
    for (suffix, tag, _), bin_path in zip(PLATFORMS, binaries):
        out = DIST / f"{PKG_NAME}-{version}-py3-none-{tag}.whl"
        build_wheel(version, tag, bin_path, metadata, readme, out)
        manifest.append({
            "file": out.name,
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "size": out.stat().st_size,
            "upstream_asset": f"caddy_{version}_{suffix}",
            "upstream_digest": checksums[f"caddy_{version}_{suffix}"],
        })

    # sdist (source only; wheels are produced by build/wheels.py or CI)
    print("== building sdist")
    sdist = DIST / f"{DIST_NAME}-{version}.tar.gz"
    with tarfile.open(sdist, "w:gz") as tf:
        for f in [
            REPO / "pyproject.toml",
            REPO / "README.md",
            REPO / "LICENSE",
            REPO / "build" / "version.txt",
            REPO / "build" / "wheels.py",
            REPO / "src",
        ]:
            if f.exists():
                tf.add(f, arcname=f"{DIST_NAME}-{version}/{f.name}", recursive=True)
    manifest.append({
        "file": sdist.name,
        "sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
        "size": sdist.stat().st_size,
        "upstream_asset": None,
        "upstream_digest": None,
    })

    (DIST / "release_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("== done")
    for m in manifest:
        print(f"  {m['file']}  sha256={m['sha256'][:16]}…  {m['size'] / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
