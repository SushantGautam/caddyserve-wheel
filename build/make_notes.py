#!/usr/bin/env python3
"""Render dist/NOTES.md (GitHub release body) from dist/release_manifest.json."""

from __future__ import annotations

import json
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist"


def main() -> None:
    v = (DIST.parent / "build" / "version.txt").read_text().strip()
    manifest = json.loads((DIST / "release_manifest.json").read_text())

    lines = [
        f"## caddyserver {v}",
        "",
        f"Caddy **v{v}** — official binaries, digest-verified against the upstream",
        f"[caddyserver/caddy v{v} release](https://github.com/caddyserver/caddy/releases/tag/v{v}).",
        "",
        "| File | Wheel SHA-256 | Upstream asset | Upstream digest (SHA-512) |",
        "|---|---|---|---|",
    ]
    for m in manifest:
        lines.append(
            f"| {m['file']} | `{m['sha256']}` | {m['upstream_asset'] or '-'} | "
            f"`{m['upstream_digest'] or '-'}` |"
        )
    (DIST / "NOTES.md").write_text("\n".join(lines) + "\n")
    print("wrote dist/NOTES.md")


if __name__ == "__main__":
    main()
