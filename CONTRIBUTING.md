<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contributing

Please follow the [KDE Code of Conduct](https://kde.org/code-of-conduct/).

KlipperQR turns the text you copied into a QR code. See the
[README](README.md) for what the app is (there is no separate product
summary document yet) and the
[KDE Human Interface Guidelines](https://develop.kde.org/hig/) for how the
interface should look and behave.

## Workflow

- The project works directly on `main`: no branches and no pull requests.
  Commit small, one issue per commit, and put the issue number in the message
  (for example `Add QR generator service (#4)`).
- Work comes from the GitHub issues. Each issue has acceptance criteria and a
  Definition of done; its last item is "App runs; checks listed in
  CONTRIBUTING pass", which means the table in the next section.
- If an issue is unclear, comment on it and add the `needs-clarification`
  label instead of guessing.
- Do not push with failing checks. CI runs on every push to `main`.

## Setup and run

```sh
python3 -m venv --system-site-packages .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python3 src/klipperqr/main.py
```

Kirigami is not a pip package; install it with your distribution (see
[README](README.md)). To run the app as a Flatpak instead, see
[docs/flatpak.md](docs/flatpak.md).

## The checks

CI (`.github/workflows/ci.yml`) runs the checks below on every push to `main`.
Run the same commands locally from the repository root before you push.
A change is done when all of them pass.

Set up the virtual environment first (see "Setup and run" above).

System tools (not on PyPI): `appstreamcli` (package `appstream`),
`desktop-file-validate` (package `desktop-file-utils`), and for the last
check `flatpak` + `flatpak-builder` (see [docs/flatpak.md](docs/flatpak.md)).

On a bare Debian/Ubuntu machine the tests also need the system libraries that
the PySide6 wheels load (`libegl1 libgl1 libopengl0 libxkbcommon0
libfontconfig1 libdbus-1-3`); without them `import PySide6.QtGui` fails with
`libEGL.so.1: cannot open shared object file`. CI installs them. CI builds the
Flatpak inside Flathub's `flatpak-github-actions:kde-6.11` container because
the `appstream` shipped with Ubuntu 24.04 fails `appstreamcli compose`.

| Check | Command |
| --- | --- |
| REUSE (licenses, SPDX headers) | `reuse lint` |
| Python lint | `ruff check .` |
| Python format | `ruff format --check .` (fix with `ruff format .`) |
| Tests | `pytest` (collects only `tests/`) |
| Desktop file | `desktop-file-validate data/io.github.octaviobernal.KlipperQR.desktop` |
| AppStream | `appstreamcli validate --no-net data/io.github.octaviobernal.KlipperQR.metainfo.xml` |
| Flatpak build | `flatpak-builder --user --force-clean --disable-rofiles-fuse --install-deps-from=flathub build-dir flatpak/io.github.octaviobernal.KlipperQR.yaml` |

Keep this table in sync with `.github/workflows/ci.yml`: when you add or
change a CI step, change the row here in the same commit.

Every new file needs an SPDX header (`reuse lint` fails otherwise). Copy the
header from an existing file of the same type.

## Tests

Tests are pytest files in `tests/`, named `test_*.py`. Put logic in Python
classes and test those directly; QML should stay thin. Tests that import
`PySide6.QtGui` or `QtQml` should run headless, as CI does:

```sh
QT_QPA_PLATFORM=offscreen pytest
```

A change that adds behavior adds or updates a test for it.

## Privacy rules

These apply to code, tests, logs and documentation examples.

- Clipboard content is sensitive. Never log it (no `print`, no logging calls,
  no exception messages that include it), never write it to disk and never
  send it anywhere.
- No network access. The app makes no network requests and the Flatpak does
  not request the network permission.
- No history by default. The app shows the QR code for the current clipboard
  text only; keeping past entries would need an explicit issue and an opt-in.
- Do not store clipboard text, or anything derived from it, in settings.

## QR code colors

QR codes are always dark modules on a light background with a quiet zone
(empty border), even in dark mode. They must not follow the Kirigami/Plasma
theme: scanners need that contrast. This is the one documented exception to
"no hardcoded colors". Every other color, font and spacing comes from
`Kirigami.Theme` and `Kirigami.Units`.

## Translatable strings

The approach is decided in [docs/i18n-settings.md](docs/i18n-settings.md): Qt
tooling (`.ts` source catalogs compiled to `.qm`), not KDE's KI18n, which has
no PySide6 bindings. Source language is English.

What you do today, for every user-visible string:

- In QML use `qsTr("text")`; add a `//:` comment line above it to give
  translators context. Plurals: `qsTr("%n item(s)", "", count)`.
- In Python use `self.tr("text")` inside a `QObject`, or
  `QCoreApplication.translate("Context", "text")` elsewhere.
- Use plain string literals with `%1` / `%n` placeholders. Extraction does not
  see `self.tr(variable)` or concatenated text.

Status of the rest (do not rely on it yet):

- Not implemented: the `translations/` folder, loading a translator in
  `main.py`, installing `.qm` files in the Flatpak and a CI check that the
  catalogs are current. These are issues #12, #13 and #14.
- Open decision: whether the catalog format stays `.ts` or becomes gettext
  `.po` is issue #16. Until it is settled, wrapping strings as above is safe
  for both.
- When #12 lands, the intended commands are the ones in
  [docs/i18n-settings.md](docs/i18n-settings.md) ("How a contributor runs
  it"): `pyside6-lupdate qml/*.qml src/klipperqr/*.py -ts
  translations/klipperqr_<lang>.ts`, translate in `pyside6-linguist`, then
  `pyside6-lrelease`. This will be moved here once it exists.

## Manual clipboard tests

Clipboard behavior depends on Wayland, X11 and Flatpak. The manual test
checklist is planned in issue #17 and will be linked here. Background:
[docs/clipboard.md](docs/clipboard.md).
