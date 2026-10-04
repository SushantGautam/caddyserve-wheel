# caddyserver

The [Caddy](https://caddyserver.com/) web server as platform-specific Python wheels.
`pip`/`uv` picks the right binary for your OS and architecture automatically.
No mise, no Docker, no Homebrew, no first-run download — **works offline after install**.

> [!IMPORTANT]
> **This is a community-maintained packaging project, not the Caddy project.**
> The official project lives at https://caddyserver.com and
> https://github.com/caddyserver/caddy. The binaries in this package are the
> official Caddy builds, redistributed as Python wheels for convenience.

| Platform | Binary |
|---|---|
| Windows (Intel/AMD) | `caddy.exe` |
| Windows (ARM64) | `caddy.exe` |
| macOS (Intel) | `caddy` |
| macOS (Apple Silicon) | `caddy` |
| Linux (x86-64, glibc or musl) | `caddy` |
| Linux (ARM64, glibc or musl) | `caddy` |

The package **version mirrors the Caddy version** (e.g. `caddyserver==2.11.7` bundles Caddy v2.11.7).

## Install

```console
pip install caddyserver            # or pipx install caddyserver
uvx caddyserver version            # run ad-hoc without installing
uv tool install caddyserver        # persistent install on PATH
```

The wheel places the real `caddy` binary on your PATH (in the venv/pipx
`bin/` directory), so you can use `caddy` normally:

```console
caddy version
caddy file-server --listen :8080
caddy adapt / validate / run ... # full official CLI passthrough
```

A `caddyserver` console script (same CLI, Python launcher) is also provided
for environments where `bin/` is not on PATH — `uvx caddyserver version`
just works.

### Programmatic use

```python
from caddyserver import get_caddy_executable
exe = get_caddy_executable()  # Path to the bundled binary
```

## Maintenance & version freshness

I am committed to keeping this package on the **latest Caddy release** — a bump
is a one-line change plus a tag, and the release pipeline builds, verifies, and
publishes automatically.

**If I am slow to pick up a new Caddy release, please
[open an issue](https://github.com/SushantGautam/caddyserver/issues) — a nudge is
all it takes and I will push a new version promptly.** Pull requests that bump
`build/version.txt` are welcome too.

## Verification

Every release artifact lists, in the GitHub release notes, both the
**wheel SHA-256** and the **upstream Caddy asset digest** from the official
[`caddyserver/caddy` release checksums](https://github.com/caddyserver/caddy/releases).
The build fails hard if any downloaded asset's digest doesn't match.

## Version bump

Edit one file, tag, done:

```bash
echo "2.12.0" > build/version.txt
git commit -am "bump to 2.12.0"
git tag v2.12.0
git push --tags     # CI builds, verifies, and publishes a GitHub Release
```

Also keep `pyproject.toml` `version` and `src/caddyserver/__init__.py`
`__version__` in sync — CI fails fast on a mismatch.

## Relationship to caddyserver-bin

Inspired by [Bing-su/pip-binary-factory](https://github.com/Bing-su/pip-binary-factory)
(author Dowon) and its `caddyserver-bin` distribution. Differences: this project
ships **vanilla official Caddy** (no custom plugins) and is maintained
independently so versions track upstream releases directly.

## Legal

Bundled binaries are official Caddy builds (Apache-2.0, Caddy Server Pty Ltd).
This project's code and packaging are MIT.
