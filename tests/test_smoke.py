# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_qml_main_exists():
    from klipperqr.main import QML_MAIN

    assert QML_MAIN.is_file()


def test_pyside6_available():
    assert importlib.util.find_spec("PySide6") is not None


def test_manifest_has_no_broad_permissions():
    text = (ROOT / "flatpak" / "io.github.octaviobernal.KlipperQR.yaml").read_text()
    for forbidden in ("--share=network", "--filesystem=", "--socket=x11"):
        assert forbidden not in text
