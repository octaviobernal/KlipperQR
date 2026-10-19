# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Load qml/Main.qml offscreen (like CI) and fail on any QML error or warning."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QUrl, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

from klipperqr.main import QML_MAIN, expose_services  # noqa: E402


def test_main_qml_loads_without_errors():
    app = QGuiApplication.instance() or QGuiApplication([])
    messages = []
    previous = qInstallMessageHandler(lambda mode, ctx, msg: messages.append(msg))
    try:
        engine = QQmlApplicationEngine()
        services = expose_services(engine)  # noqa: F841
        engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
        app.processEvents()
        roots = engine.rootObjects()
        assert roots, "Main.qml failed to load:\n" + "\n".join(messages)
        window = roots[0]
        assert window.property("title") == "KlipperQR"
        assert window.property("hasText") is False
        assert window.property("minimumWidth") > 0
        # Exposed clipboard state follows the Python service.
        clipboard_service = services[0]
        assert window.property("clipboardState") == clipboard_service.state
        window.close()
    finally:
        qInstallMessageHandler(previous)
    errors = [m for m in messages if "Main.qml" in m or "qml" in m.lower()]
    assert not errors, "\n".join(errors)
