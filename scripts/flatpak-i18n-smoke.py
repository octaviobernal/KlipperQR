# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Headless check that the installed Flatpak shows Spanish labels.

Run inside the sandbox with LANG=es_ES.UTF-8 (see docs/flatpak.md). It loads
the real Main.qml with the translator the app itself installs and prints only
fixed UI labels (never clipboard content). Exit code 0 means the installed
.qm was found and the toolbar labels are Spanish.
"""

import sys

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from klipperqr.main import (
    QML_MAIN,
    expose_services,
    install_translator,
    translation_dirs,
)


def main() -> int:
    app = QGuiApplication(sys.argv)
    print("search dirs:", [str(d) for d in translation_dirs()])
    translator = install_translator(app)
    print("translator installed:", translator is not None)
    engine = QQmlApplicationEngine()
    services = expose_services(engine)  # noqa: F841
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    roots = engine.rootObjects()
    if not roots:
        return 1
    texts = {
        o.property("text")
        for o in roots[0].findChildren(QObject)
        if isinstance(o.property("text"), str)
    }
    expected = {"Guardar", "Copiar imagen", "Borrar", "Pegar"}
    print("labels found:", sorted(expected & texts))
    return 0 if expected <= texts and "Paste" not in texts else 1


if __name__ == "__main__":
    sys.exit(main())
