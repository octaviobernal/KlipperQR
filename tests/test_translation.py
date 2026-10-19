# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Translation loading: a compiled Spanish catalog changes labels in Main.qml.

tests/data/klipperqr_es.ts is a 4-string fixture (not a shipped translation).
It is compiled with pyside6-lrelease into a temporary folder for each test.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QLocale, QObject, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

from klipperqr.main import QML_MAIN, expose_services, install_translator  # noqa: E402

LRELEASE = shutil.which("pyside6-lrelease")
pytestmark = pytest.mark.skipif(LRELEASE is None, reason="pyside6-lrelease not found")


@pytest.fixture
def qm_dir(tmp_path):
    subprocess.run(
        [
            LRELEASE,
            str(ROOT / "tests" / "data" / "klipperqr_es.ts"),
            "-qm",
            str(tmp_path / "klipperqr_es.qm"),
        ],
        check=True,
        capture_output=True,
    )
    return tmp_path


def label_texts(app, locale, search_dirs):
    """Load Main.qml with the translator for `locale`; return all 'text' values."""
    translator = install_translator(app, locale, search_dirs)
    engine = QQmlApplicationEngine()
    services = expose_services(engine)  # noqa: F841
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    roots = engine.rootObjects()
    assert roots
    window = roots[0]
    texts = {
        o.property("text")
        for o in window.findChildren(QObject)
        if isinstance(o.property("text"), str)
    }
    window.close()
    if translator is not None:
        app.removeTranslator(translator)
    return texts


def test_spanish_catalog_changes_labels(qm_dir):
    app = QGuiApplication.instance() or QGuiApplication([])
    texts = label_texts(app, QLocale("es_ES"), [qm_dir])
    assert {"Guardar", "Copiar imagen", "Borrar", "Pegar"} <= texts
    assert "Paste" not in texts


def test_unsupported_locale_falls_back_to_english(qm_dir):
    app = QGuiApplication.instance() or QGuiApplication([])
    assert install_translator(app, QLocale("de_DE"), [qm_dir]) is None
    texts = label_texts(app, QLocale("de_DE"), [qm_dir])
    assert {"Save", "Copy image", "Clear", "Paste"} <= texts


def test_missing_or_empty_directory_is_not_an_error(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication([])
    missing = tmp_path / "does-not-exist"
    assert install_translator(app, QLocale("es_ES"), [missing, tmp_path]) is None


def test_default_search_dirs_end_with_checkout_translations():
    from klipperqr.main import translation_dirs

    assert translation_dirs()[-1] == ROOT / "translations"
    assert (ROOT / "translations" / "klipperqr_en.ts").is_file()
