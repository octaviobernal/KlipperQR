# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Headless check that QR generation works inside the built Flatpak.

Run it inside the sandbox with the network denied (see docs/flatpak.md). It
uses a fixed example URL (never clipboard content) and prints only metadata.
Exit code 0 means: segno imports from the app's own site-packages, a PNG and
an SVG come out, and the network is reported as denied. Any other connection error
(timeout, refused, ...) is an error and gives a non-zero exit code.
"""

import errno
import socket
import sys

import segno
from PySide6.QtCore import QCoreApplication

from klipperqr.qr_service import QrState, generate_qr

# Errors that mean "the sandbox has no network". Anything else (timeout,
# connection refused, ...) is unexpected and must not be read as "denied".
_DENIED_ERRNOS = {errno.ENETUNREACH, errno.EACCES, errno.EPERM}


def _is_network_denied(error: OSError) -> bool:
    if isinstance(error, socket.gaierror):
        return True  # all EAI_* codes: name resolution is not possible
    return error.errno in _DENIED_ERRNOS


def _check_offline() -> str:
    """Return "denied", "reachable" or "error:<ErrnoName>"."""
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3).close()
    except OSError as error:
        if _is_network_denied(error):
            return "denied"
        name = errno.errorcode.get(error.errno or 0, type(error).__name__)
        return f"error:{name}"
    return "reachable"


def main() -> int:
    _app = QCoreApplication([])
    result = generate_qr("https://example.org/")
    png_ok = result.png.startswith(b"\x89PNG\r\n\x1a\n")
    svg_ok = "<svg" in result.svg
    network = _check_offline()
    print(f"segno {segno.__version__} from {segno.__file__}")
    print(f"state={result.state.name} png_bytes={len(result.png)}")
    print(f"svg_chars={len(result.svg)}")
    print(f"png_ok={png_ok} svg_ok={svg_ok} network={network}")
    return (
        0
        if (result.state is QrState.OK and png_ok and svg_ok and network == "denied")
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
