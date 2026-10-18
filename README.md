<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# KlipperQR

A KDE Plasma 6 app that turns the text or link you just copied into a QR code you can scan with your phone.

Built with Python, PySide6 and Kirigami, and distributed as a Flatpak.

Status: early development.

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
