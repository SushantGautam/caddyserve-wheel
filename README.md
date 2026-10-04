# caddyserver

The [Caddy](https://caddyserver.com/) web server as a Python wheel — install with
`pip`/`uvx`, no mise, no Docker, no Homebrew, no first-run download.
**Works offline after install.** `pip`/`uv` picks the right binary for your OS
and architecture automatically (Windows, macOS, Linux; x86-64 and ARM64).

> [!IMPORTANT]
> **Community-maintained, not the Caddy project.** Official project:
> https://caddyserver.com / https://github.com/caddyserver/caddy. The binaries
> here are the official Caddy builds, repackaged as wheels.
> **Handover:** happy to **hand over the `caddyserver` PyPI project to the
> official Caddy team** if they want to maintain it — open an issue.

## Quick start

```console
# one-shot, no install (uv):
uvx caddyserver version

# or install:
pip install caddyserver
caddy version
```

## CLI usage

The wheel puts the real `caddy` binary on your PATH, so the full official CLI
works as-is:

```console
caddy version                        # show version
caddy file-server --listen :8080     # serve the current directory
caddy run --config Caddyfile         # start with your Caddyfile
caddy validate --config Caddyfile    # check config syntax
caddy adapt --config Caddyfile       # Caddyfile -> JSON
caddy list modules                   # list compiled-in modules
```

Any `caddy` subcommand works — this is the unmodified official binary.
A `caddyserver` console script does the same thing (Python launcher), useful
when `bin/` is not on PATH: `uvx caddyserver version`.

### Programmatic use

```python
from caddyserver import get_caddy_executable
exe = get_caddy_executable()  # Path to the bundled caddy binary
```

## Install options

```console
uvx caddyserver <args>             # ad-hoc, no install
uv tool install caddyserver        # persistent, on PATH
pipx install caddyserver           # persistent, on PATH
pip install caddyserver            # inside a project/venv
```

The package **version mirrors the Caddy version**
(e.g. `caddyserver==2.11.7` bundles Caddy v2.11.7).

## Maintenance

Committed to tracking the **latest Caddy release** — a bump is one line plus a
tag, and the pipeline builds, verifies, and publishes automatically.
**If I am slow to pick up a new Caddy release, [open an issue](https://github.com/SushantGautam/caddyserve-wheel/issues) —
I will push a new version promptly.** PRs bumping `build/version.txt` welcome.

## Verification

Every GitHub Release lists the **wheel SHA-256** and the **upstream Caddy
asset digest** for each file; the build fails hard if any downloaded asset
doesn't match the [official checksums](https://github.com/caddyserver/caddy/releases).

## Version bump (maintainers)

```bash
echo "2.12.0" > build/version.txt
# also update pyproject.toml version + src/caddyserver/__init__.py __version__
git commit -am "bump to 2.12.0"
git tag v2.12.0 && git push --tags   # CI builds, verifies, publishes
```
