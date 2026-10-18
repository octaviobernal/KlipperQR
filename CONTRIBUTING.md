<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contributing

Please follow the [KDE Code of Conduct](https://kde.org/code-of-conduct/).

## The checks

CI (`.github/workflows/ci.yml`) runs the checks below on every push to `main`.
Run the same commands locally from the repository root before you push.
A change is done when all of them pass.

One-time setup:

```sh
python3 -m venv --system-site-packages .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
```

System tools (not on PyPI): `appstreamcli` (package `appstream`),
`desktop-file-validate` (package `desktop-file-utils`), and for the last
check `flatpak` + `flatpak-builder` (see [docs/flatpak.md](docs/flatpak.md)).

| Check | Command |
| --- | --- |
| REUSE (licenses, SPDX headers) | `reuse lint` |
| Python lint | `ruff check .` |
| Python format | `ruff format --check .` (fix with `ruff format .`) |
| Tests | `pytest` (collects only `tests/`) |
| Desktop file | `desktop-file-validate data/io.github.octaviobernal.KlipperQR.desktop` |
| AppStream | `appstreamcli validate --no-net data/io.github.octaviobernal.KlipperQR.metainfo.xml` |
| Flatpak build | `flatpak-builder --user --force-clean --disable-rofiles-fuse --install-deps-from=flathub build-dir flatpak/io.github.octaviobernal.KlipperQR.yaml` |

Every new file needs an SPDX header (`reuse lint` fails otherwise).
Clipboard content is sensitive: never log, store or send it.
