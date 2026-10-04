"""caddyserver: official Caddy binaries distributed as Python wheels.

The package version mirrors the bundled Caddy version.
"""

__version__ = "2.11.7"
CADDY_VERSION = __version__

from caddyserver.cli import get_caddy_executable, main  # noqa: E402,F401
