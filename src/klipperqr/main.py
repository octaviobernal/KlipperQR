# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Application entry point. Run with: python3 src/klipperqr/main.py"""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

APP_ID = "io.github.octaviobernal.KlipperQR"
QML_MAIN = Path(__file__).resolve().parents[2] / "qml" / "Main.qml"


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("KlipperQR")
    app.setDesktopFileName(APP_ID)

    engine = QQmlApplicationEngine()
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
