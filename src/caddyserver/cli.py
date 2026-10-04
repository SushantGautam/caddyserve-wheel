"""Console entry point: locate the bundled Caddy binary and exec it.

The binary ships inside the wheel under ``.data/scripts/`` and is installed
by pip into the same directory as the interpreter's executable
(venv/pipx ``bin/`` on POSIX, the Scripts-less venv root on Windows).
"""

from __future__ import annotations

import os
import sys
import sysconfig
from pathlib import Path

_BIN = "caddy.exe" if os.name == "nt" else "caddy"


class CaddyNotFound(Exception):
    pass


def get_caddy_executable() -> Path:
    """Return the path to the bundled Caddy binary."""
    candidates = []

    # Primary: pip installs .data/scripts/ into the scheme scripts dir,
    # which is exactly where the `caddy`/`caddyserver` console scripts live.
    # (Do NOT resolve sys.executable: venvs symlink the interpreter to the
    # base install, which would point at the wrong bin/.)
    candidates.append(Path(sysconfig.get_path("scripts")) / _BIN)
    candidates.append(Path(sys.executable).parent / _BIN)

    # Fallbacks: relative to this package (uninstalled tree, exotic layouts).
    # `pkg` is the caddyserver package dir; `pkg.parent` is site-packages.
    pkg = Path(__file__).resolve().parent
    sp = pkg.parent
    candidates += [
        sp / _BIN,
        pkg / _BIN,
        # uv (uvx / `uv tool install`) leaves the .data tree under
        # site-packages instead of moving it to the scheme scripts dir.
        sp / ".data" / "scripts" / _BIN,
        sp / "data" / "scripts" / _BIN,
        pkg.parent.parent / "bin" / _BIN,
    ]

    for c in candidates:
        c = c.resolve() if c.exists() else c
        if c.is_file():
            return c

    raise CaddyNotFound(
        "Bundled Caddy binary not found. Looked for:\n  "
        + "\n  ".join(str(c) for c in candidates)
        + "\nWas this package installed from a platform wheel, not the source tree?"
    )


def main(argv: list[str] | None = None) -> int:
    exe = get_caddy_executable()
    args = sys.argv[1:] if argv is None else argv
    os.execvp(str(exe), [str(exe), *args])
    # Unreachable on success; execvp raises on failure.
