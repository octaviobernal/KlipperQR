# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Application entry point. Run with: python3 src/klipperqr/main.py"""

import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QStandardPaths, QTranslator, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

APP_ID = "io.github.octaviobernal.KlipperQR"

# Settings identity (issue #15). Qt builds the settings file path from these
# two names (<config dir>/<ORGANIZATION_NAME>/<APPLICATION_NAME>.conf).
# Fixed for 1.0: do NOT change them afterwards without a settings migration,
# or users lose their saved settings. See docs/i18n-settings.md.
# Setting the names does not use QSettings and writes no file by itself.
ORGANIZATION_NAME = "io.github.octaviobernal"
APPLICATION_NAME = "KlipperQR"


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


def translation_dirs() -> list[Path]:
    """Folders that may hold the compiled `klipperqr_<lang>.qm` files.

    Installed (e.g. Flatpak): <data dir>/klipperqr/translations, found through
    QStandardPaths (/app/share/klipperqr/translations in the Flatpak).
    Source checkout fallback: <repo>/translations.
    """
    dirs = [
        Path(p)
        for p in QStandardPaths.locateAll(
            QStandardPaths.StandardLocation.GenericDataLocation,
            "klipperqr/translations",
            QStandardPaths.LocateOption.LocateDirectory,
        )
    ]
    dirs.append(Path(__file__).resolve().parents[2] / "translations")
    return dirs


def install_translator(app, locale=None, search_dirs=None):
    """Install one QTranslator for the system locale; return it or None.

    Call before the QML is loaded. A missing .qm or an unsupported locale is
    not an error: nothing is installed and the English source text is shown.
    No message ever includes clipboard content.
    """
    locale = QLocale() if locale is None else locale
    for directory in translation_dirs() if search_dirs is None else search_dirs:
        translator = QTranslator(app)
        if translator.load(locale, "klipperqr", "_", str(directory)):
            app.installTranslator(translator)
            return translator
        translator.deleteLater()
    return None


def expose_services(engine):
    """Create the services and expose them to QML as context properties.

    setContextProperty does NOT take ownership, so each service is parented
    to the engine (Qt then owns it and the Python wrapper cannot be garbage
    collected while the engine lives) and also returned so main() can hold a
    reference for the whole run. Used by main() and by the regression test.
    """
    try:
        from klipperqr.app_info import AppInfo
        from klipperqr.clipboard_service import ClipboardService
        from klipperqr.qr_service import QrService
    except ImportError:  # run as `python3 src/klipperqr/main.py`
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from klipperqr.app_info import AppInfo
        from klipperqr.clipboard_service import ClipboardService
        from klipperqr.qr_service import QrService

    clipboard_service = ClipboardService(parent=engine)
    qr_service = QrService(engine)
    context = engine.rootContext()
    context.setContextProperty("clipboardService", clipboard_service)
    context.setContextProperty("qrService", qr_service)
    # Parented to the engine, so Qt keeps it alive; not part of the return value.
    context.setContextProperty("appInfo", AppInfo(APP_ID, engine))
    return clipboard_service, qr_service


def set_app_identity(app) -> None:
    """Set the organization and application names, once, at startup."""
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationName(APPLICATION_NAME)


def main() -> int:
    app = QGuiApplication(sys.argv)
    set_app_identity(app)
    app.setDesktopFileName(APP_ID)
    # Before the QML is loaded, so qsTr() sees the translation.
    install_translator(app)

    engine = QQmlApplicationEngine()
    # Local variables keep both services alive until main() returns.
    clipboard_service, qr_service = expose_services(engine)  # noqa: F841
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    clipboard_service.attach_window(window)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
