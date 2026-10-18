# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Application entry point. Run with: python3 src/klipperqr/main.py"""

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

APP_ID = "io.github.octaviobernal.KlipperQR"


def find_qml_main() -> Path:
    """Locate Main.qml in a source checkout or in an installed location.

    Checkout: <repo>/qml/Main.qml (two levels above src/klipperqr).
    Installed (e.g. Flatpak): <prefix>/share/klipperqr/qml/Main.qml, found
    through the XDG data directories (/app/share inside the Flatpak).
    """
    checkout = Path(__file__).resolve().parents[2] / "qml" / "Main.qml"
    if checkout.is_file():
        return checkout
    installed = QStandardPaths.locate(
        QStandardPaths.StandardLocation.GenericDataLocation,
        "klipperqr/qml/Main.qml",
    )
    return Path(installed) if installed else checkout


QML_MAIN = find_qml_main()


def main() -> int:
    try:
        from klipperqr.clipboard_service import ClipboardService
    except ImportError:  # run as `python3 src/klipperqr/main.py`
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from klipperqr.clipboard_service import ClipboardService

    app = QGuiApplication(sys.argv)
    app.setApplicationName("KlipperQR")
    app.setDesktopFileName(APP_ID)

    engine = QQmlApplicationEngine()
    clipboard_service = ClipboardService()
    engine.rootContext().setContextProperty("clipboardService", clipboard_service)
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    clipboard_service.attach_window(window)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
