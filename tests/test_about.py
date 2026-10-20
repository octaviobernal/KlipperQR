# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""About page: version single source of truth, links, and the QML page."""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

import klipperqr  # noqa: E402
from klipperqr.app_info import AppInfo  # noqa: E402
from klipperqr.main import APP_ID, QML_MAIN, expose_services  # noqa: E402

METAINFO = ROOT / "data" / (APP_ID + ".metainfo.xml")


def _metainfo():
    return ET.parse(METAINFO).getroot()


def test_version_matches_newest_release_in_metainfo():
    releases = _metainfo().findall("releases/release")
    assert releases
    newest = max(releases, key=lambda r: r.get("date"))
    assert newest.get("version") == klipperqr.__version__


def test_links_match_metainfo():
    root = _metainfo()
    info = AppInfo(APP_ID)
    assert info.homepage == root.findtext("url[@type='homepage']")
    assert info.bugTracker == root.findtext("url[@type='bugtracker']")
    assert info.version == klipperqr.__version__
    assert info.appId == APP_ID
    assert info.segnoVersion  # segno is a hard dependency


def test_about_action_opens_page_once():
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    services = expose_services(engine)  # noqa: F841
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    window = engine.rootObjects()[0]
    window.show()
    app.processEvents()

    action = window.findChild(object, "aboutAction")
    assert action is not None
    assert action.property("text") == "About KlipperQR"

    assert window.property("pageDepth") == 1
    action.trigger(None)
    app.processEvents()
    assert window.property("pageDepth") == 2
    action.trigger(None)  # a second trigger must not stack another page
    app.processEvents()
    assert window.property("pageDepth") == 2

    page = window.findChild(object, "aboutPage")
    assert page is not None
    data = page.property("aboutData").toVariant()
    assert data["version"] == klipperqr.__version__
    assert data["version"] != ""
    assert data["homepage"].startswith("https://")
    assert data["bugAddress"].startswith("https://")
    assert data["licenses"][0]["spdx"] == "GPL-3.0-or-later"
    assert "segno" in data["components"][0]["name"]
    assert "BSD-3-Clause" in data["components"][0]["name"]
    assert "Nothing you copy or type is sent anywhere" in data["otherText"]
    window.close()
