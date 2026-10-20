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


def test_shipped_spanish_catalog_is_complete_and_changes_labels(tmp_path):
    ts = ROOT / "translations" / "klipperqr_es.ts"
    assert "unfinished" not in ts.read_text(encoding="utf-8")
    subprocess.run(
        [LRELEASE, str(ts), "-qm", str(tmp_path / "klipperqr_es.qm")],
        check=True,
        capture_output=True,
    )
    app = QGuiApplication.instance() or QGuiApplication([])
    texts = label_texts(app, QLocale("es_ES"), [tmp_path])
    assert {"Guardar", "Copiar imagen", "Borrar", "Pegar"} <= texts
    assert "Paste" not in texts


def _run_install_script(tmp_path, with_ts):
    """Run flatpak/install-translations.sh in a scratch tree with an `lrelease`
    shim that forwards to pyside6-lrelease (the SDK ships the real `lrelease`)."""
    work = tmp_path / "work"
    (work / "translations").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "lrelease"
    shim.write_text(f'#!/bin/sh\nexec "{LRELEASE}" "$@"\n')
    shim.chmod(0o755)
    if with_ts:
        shutil.copy(ROOT / "tests" / "data" / "klipperqr_es.ts", work / "translations")
    dest = tmp_path / "dest"
    result = subprocess.run(
        ["sh", str(ROOT / "flatpak" / "install-translations.sh"), str(dest)],
        cwd=work,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
    )
    return result, dest


def test_install_script_installs_compiled_catalogs(tmp_path):
    result, dest = _run_install_script(tmp_path, with_ts=True)
    assert result.returncode == 0, result.stderr
    assert (dest / "klipperqr_es.qm").stat().st_size > 0


def test_install_script_fails_without_catalogs(tmp_path):
    result, dest = _run_install_script(tmp_path, with_ts=False)
    assert result.returncode != 0
    assert "no translations" in result.stderr
    assert not dest.exists()


def test_manifest_runs_the_install_script():
    manifest = (ROOT / "flatpak" / "io.github.octaviobernal.KlipperQR.yaml").read_text()
    assert (
        "flatpak/install-translations.sh /app/share/klipperqr/translations" in manifest
    )
