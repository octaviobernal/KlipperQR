# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Flathub manifest must match the local one except for the app source."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "io.github.octaviobernal.KlipperQR.yaml"


def _body(text: str) -> str:
    """Manifest without comments and without the final klipperqr source."""
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    joined = "\n".join(lines)
    return joined.split("    sources:\n      - type: dir")[0].split(
        "    sources:\n      - type: git"
    )[0]


def test_flathub_manifest_matches_local_manifest():
    local = (ROOT / "flatpak" / NAME).read_text()
    flathub = (ROOT / "flatpak" / "flathub" / NAME).read_text()
    # The segno module comes first and contains its own "sources:", so compare
    # everything before the last module's sources.
    assert _body(local) == _body(flathub)


def test_flathub_manifest_uses_pinned_git_source():
    text = (ROOT / "flatpak" / "flathub" / NAME).read_text()
    assert "type: dir" not in text
    assert "url: https://github.com/octaviobernal/KlipperQR.git" in text
    assert re.search(r"^\s+tag: v\d+\.\d+\.\d+$", text, re.MULTILINE)
    assert re.search(r"^\s+commit: \S+$", text, re.MULTILINE)
    assert "--share=network" not in text


def test_metainfo_screenshots_are_pinned_to_a_tag():
    text = (
        ROOT / "data" / "io.github.octaviobernal.KlipperQR.metainfo.xml"
    ).read_text()
    urls = re.findall(r"<image[^>]*>([^<]+)</image>", text)
    assert urls
    for url in urls:
        assert "/KlipperQR/v" in url
        assert "/main/" not in url
