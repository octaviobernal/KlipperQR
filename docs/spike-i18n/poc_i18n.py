# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Throwaway spike (#5): Qt translations (.ts/.qm) and QSettings.

Usage (from the repository root):
    pyside6-lrelease docs/spike-i18n/klipperqr_es.ts -qm /tmp/x/klipperqr_es.qm
    KLIPPERQR_LANG=es python3 docs/spike-i18n/poc_i18n.py /tmp/x [--print]

Never touches clipboard content. Settings keys are harmless examples.
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication, QLocale, QObject, QSettings, QTranslator, QUrl, Property,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class Backend(QObject):
    """Shows that strings marked in Python (self.tr) are translated too."""

    @Property(str, constant=True)
    def message(self):
        # Context = class name "Backend" (what pyside6-lupdate extracts).
        return self.tr("Message from Python")

    @Property(int, constant=True)
    def count(self):
        return 3


def main() -> int:
    qm_dir = Path(sys.argv[1])
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("KlipperQRSpike")  # sets the QSettings path
    app.setApplicationName("klipperqr-spike")

    settings = QSettings()
    print("settings file:", settings.fileName())
    lang = os.environ.get("KLIPPERQR_LANG") or settings.value("language", "")
    translator = QTranslator(app)
    locale = QLocale(lang) if lang else QLocale()
    ok = translator.load(locale, "klipperqr", "_", str(qm_dir))
    print("locale:", locale.name(), "translator loaded:", ok)
    if ok:
        app.installTranslator(translator)
    settings.setValue("lastTestRun", "ok")
    settings.sync()

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("pocBackend", backend)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Poc.qml"))))
    if not engine.rootObjects():
        return 1
    if "--print" in sys.argv:
        root = engine.rootObjects()[0]
        for name in ("greeting", "plural", "fromPython"):
            print(name, "=", root.findChild(QObject, name).property("text"))
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
