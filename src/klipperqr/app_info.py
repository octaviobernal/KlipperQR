# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Facts about the app (version, links) shown on the About page.

KAboutData has no official PySide6 bindings, so this small QObject feeds the
plain JavaScript object that Kirigami.AboutPage accepts instead. Only the
non-translatable facts live here; the visible sentences are wrapped with
qsTr() in qml/KlipperAboutPage.qml.
"""

from importlib import metadata

from PySide6.QtCore import Property, QObject

from klipperqr import __version__

HOMEPAGE = "https://github.com/octaviobernal/KlipperQR"
BUG_TRACKER = "https://github.com/octaviobernal/KlipperQR/issues"


def segno_version() -> str:
    """Installed segno version, or "" if it cannot be determined."""
    try:
        return metadata.version("segno")
    except metadata.PackageNotFoundError:
        return ""


class AppInfo(QObject):
    """Read-only application facts, exposed to QML as `appInfo`."""

    def __init__(self, app_id: str, parent=None):
        super().__init__(parent)
        self._app_id = app_id

    @Property(str, constant=True)
    def appId(self) -> str:
        return self._app_id

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def homepage(self) -> str:
        return HOMEPAGE

    @Property(str, constant=True)
    def bugTracker(self) -> str:
        return BUG_TRACKER

    @Property(str, constant=True)
    def segnoVersion(self) -> str:
        return segno_version()
