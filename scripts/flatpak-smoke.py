# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Headless check that QR generation works inside the built Flatpak.

Run it inside the sandbox with the network denied (see docs/flatpak.md). It
uses a fixed example URL (never clipboard content) and prints only metadata.
Exit code 0 means: segno imports from the app's own site-packages, a PNG and
an SVG come out, and the network really is unreachable.
"""

import socket
import sys

import segno
from PySide6.QtCore import QCoreApplication

from klipperqr.qr_service import QrState, generate_qr


def _network_reachable() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3).close()
    except OSError:
        return False
    return True


def main() -> int:
    _app = QCoreApplication([])
    result = generate_qr("https://example.org/")
    png_ok = result.png.startswith(b"\x89PNG\r\n\x1a\n")
    svg_ok = "<svg" in result.svg
    offline = not _network_reachable()
    print(f"segno {segno.__version__} from {segno.__file__}")
    print(f"state={result.state.name} png_bytes={len(result.png)}")
    print(f"svg_chars={len(result.svg)}")
    print(f"png_ok={png_ok} svg_ok={svg_ok} offline={offline}")
    return 0 if (result.state is QrState.OK and png_ok and svg_ok and offline) else 1


if __name__ == "__main__":
    sys.exit(main())
