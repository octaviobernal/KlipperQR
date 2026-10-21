<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# KlipperQR

A KDE Plasma 6 app that turns the text or link you just copied into a QR code you can scan with your phone.

Built with Python, PySide6 and Kirigami, and distributed as a Flatpak.

Status: early development.

The window shows the QR code and, next to it (or below it on narrow windows),
an editable box with the exact text being encoded. Edit the text and the QR
code follows. When the window regains focus, your edits are replaced only if
the clipboard text changed since the last read. The text is kept in memory
only; nothing is saved or logged.

"Copy image" (Ctrl+Shift+C) puts the QR code on the clipboard as an image. On
Wayland the image may disappear when KlipperQR closes unless a clipboard
manager keeps it.

"Save" (Ctrl+S) writes the QR code to a PNG or SVG file (dark modules on white,
with a quiet zone). The suggested name is `qrcode.png`; it never contains your
text. In the Flatpak the file dialog is the system file chooser portal, so the
app needs no filesystem permission.

## Privacy

- Nothing leaves your device: the app makes no network requests.
- Nothing is logged: the app never prints your text.
- Nothing is stored: the text stays in memory only, with no settings, cache or
  temporary files.
- There is no history: only the current text is shown.

The only file written is a PNG or SVG that you choose to save. Details and how
this is verified: [docs/privacy.md](docs/privacy.md).

License: GPL-3.0-or-later.

## Run from a checkout

Requirements: Python 3.10+, PySide6, and Kirigami (KDE Frameworks 6) installed
on the system. Kirigami is not a pip package; install it with your
distribution (see the comments in `requirements.txt`). Inside the Flatpak it
comes with the KDE runtime.

```sh
python3 -m venv --system-site-packages .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 src/klipperqr/main.py        # the single launch command
```

Run the tests with `pytest`. All checks that CI runs, and how to run them
locally, are listed in [CONTRIBUTING.md](CONTRIBUTING.md).

## Run as a Flatpak

Build and run instructions, runtime version and permissions are in
[docs/flatpak.md](docs/flatpak.md).

## Layout

- `src/klipperqr/`: Python code
- `qml/`: QML user interface
- `tests/`: pytest tests
- `flatpak/`: Flatpak manifest and launcher
- `data/`: desktop file, AppStream metainfo, placeholder icon
- `docs/`: documentation
