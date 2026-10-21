# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Check that the app ID is used consistently in all metadata files."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _app_id() -> str:
    text = (ROOT / "src" / "klipperqr" / "main.py").read_text()
    match = re.search(r'^APP_ID = "([^"]+)"', text, re.MULTILINE)
    assert match
    return match.group(1)


def test_files_named_after_app_id():
    app_id = _app_id()
    for suffix in (".desktop", ".metainfo.xml", ".svg"):
        assert (ROOT / "data" / (app_id + suffix)).is_file()
    assert (ROOT / "flatpak" / (app_id + ".yaml")).is_file()


def test_desktop_file_content():
    app_id = _app_id()
    text = (ROOT / "data" / (app_id + ".desktop")).read_text()
    assert f"Icon={app_id}" in text
    assert "Exec=klipperqr" in text
    assert re.search(r"^Categories=.+;$", text, re.MULTILINE)


def test_metainfo_content():
    app_id = _app_id()
    root = ET.parse(ROOT / "data" / (app_id + ".metainfo.xml")).getroot()
    assert root.findtext("id") == app_id
    assert root.findtext("launchable") == app_id + ".desktop"
    assert root.find("url[@type='homepage']") is not None
    assert root.findtext("project_license")


def test_manifest_uses_app_id():
    app_id = _app_id()
    text = (ROOT / "flatpak" / (app_id + ".yaml")).read_text()
    assert f"app-id: {app_id}" in text


def test_manifest_pins_segno_wheel_and_has_no_network():
    app_id = _app_id()
    text = (ROOT / "flatpak" / (app_id + ".yaml")).read_text()
    pinned = (ROOT / "requirements.txt").read_text()
    version = re.search(r"^segno==([\d.]+)$", pinned, re.MULTILINE).group(1)
    assert f"segno-{version}-py3-none-any.whl" in text
    assert re.search(r"^\s+sha256: [0-9a-f]{64}$", text, re.MULTILINE)
    assert "--no-deps" in text
    assert "pillow" not in text.lower()
    assert "--share=network" not in text


def test_manifest_installs_python_deps_offline_and_has_exact_permissions():
    app_id = _app_id()
    text = (ROOT / "flatpak" / (app_id + ".yaml")).read_text()
    pip_lines = [line for line in text.splitlines() if "pip3 install" in line]
    assert pip_lines
    for line in pip_lines:
        assert "--no-index" in line
        assert "--no-build-isolation" in line
    block = re.search(r"^finish-args:\n((?:  - .+\n)+)", text, re.MULTILINE)
    assert block
    args = [line.strip()[2:] for line in block.group(1).splitlines()]
    assert args == [
        "--socket=wayland",
        "--socket=fallback-x11",
        "--share=ipc",
        "--device=dri",
    ]


def test_manifest_does_not_install_segno_script():
    app_id = _app_id()
    text = (ROOT / "flatpak" / (app_id + ".yaml")).read_text()
    assert "rm -f ${FLATPAK_DEST}/bin/segno" in text


def test_metainfo_is_complete_for_flathub():
    root = ET.parse(ROOT / "data" / (_app_id() + ".metainfo.xml")).getroot()
    assert len(root.findall("description/p")) >= 3
    assert root.findall("keywords/keyword")
    release = root.find("releases/release")
    assert release.get("version") and release.get("date")
    shots = root.findall("screenshots/screenshot")
    assert len(shots) >= 2
    assert len(root.findall("screenshots/screenshot[@type='default']")) == 1
    for shot in shots:
        url = shot.findtext("image")
        assert url.startswith("https://")
        assert shot.findtext("caption")
        # The URL ends in a file that is committed in the repository.
        assert (ROOT / "docs" / "screenshots" / url.rsplit("/", 1)[1]).is_file()
