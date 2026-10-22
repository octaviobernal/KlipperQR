# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression test: services exposed to QML must survive garbage collection."""

import gc
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine  # noqa: E402

from klipperqr.main import expose_services  # noqa: E402

QML = b"""
import QtQml
QtObject {
    property string result: {
        if (qrService === null || clipboardService === null)
            return "null";
        qrService.generate("hi");
        return typeof clipboardService.clear + "," + qrService.state;
    }
}
"""


def test_context_services_survive_gc():
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlEngine()
    # Deliberately drop the returned references, like the buggy code did.
    expose_services(engine)
    gc.collect()

    component = QQmlComponent(engine)
    component.setData(QML, QUrl("file:///test.qml"))
    obj = component.create()
    assert obj is not None, component.errorString()
    result = obj.property("result")
    assert result.startswith("function,"), result
    assert app is not None


def test_app_identity_is_fixed_for_1_0():
    from klipperqr.main import (
        APPLICATION_NAME,
        ORGANIZATION_NAME,
        set_app_identity,
    )

    # Part of the settings file path: changing these needs a migration (#15).
    assert ORGANIZATION_NAME == "io.github.octaviobernal"
    assert APPLICATION_NAME == "KlipperQR"
    app = QGuiApplication.instance() or QGuiApplication([])
    set_app_identity(app)
    assert app.organizationName() == "io.github.octaviobernal"
    assert app.applicationName() == "KlipperQR"
