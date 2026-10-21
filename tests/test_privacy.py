# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Privacy checks (issue #31): manifest, code patterns, and a runtime run."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "flatpak" / "io.github.octaviobernal.KlipperQR.yaml"


def _finish_args():
    block = re.search(r"^finish-args:\n((?:  - .+\n)+)", MANIFEST.read_text(), re.M)
    assert block
    return [line.strip()[2:] for line in block.group(1).splitlines()]


def test_manifest_requests_no_network_filesystem_or_bus_names():
    forbidden = (
        "--share=network",
        "--filesystem",
        "--talk-name",
        "--system-talk-name",
        "--own-name",
        "--socket=session-bus",
        "--socket=system-bus",
        "--socket=ssh-auth",
        "--device=all",
    )
    for arg in _finish_args():
        assert not arg.startswith(forbidden), arg
    # Also catch them anywhere else in the file (for example a build-args block).
    text = MANIFEST.read_text()
    for word in ("--share=network", "--filesystem", "--talk-name", "--own-name"):
        assert word not in text, word


def _code_files():
    return [
        *sorted((ROOT / "src").rglob("*.py")),
        *sorted((ROOT / "qml").glob("*.qml")),
    ]


def test_no_logging_printing_settings_or_temp_files_in_app_code():
    patterns = [
        r"\bprint\s*\(",
        r"\bimport logging\b",
        r"\blogging\.",
        r"\bsys\.std(out|err)\b",
        r"\bq(Debug|Info|Warning|Critical)\b",
        r"\bconsole\.\w+",
        r"\bQSettings\b",
        r"\btempfile\b",
        r"\bQTemporary(File|Dir)\b",
        r"\bQSaveFile\b",
        r"\bQFile\b",
        r"\bpickle\b|\bshelve\b|\bsqlite3\b",
        r"(?<![.\w])open\s*\(",
        r"\bwrite_text\b",
        r"\burllib\b|\bsocket\b|\bhttp\.client\b|\brequests\b|QNetwork|XMLHttpRequest",
    ]
    hits = []
    for path in _code_files():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0] if path.suffix == ".py" else line.split("//")[0]
            for pattern in patterns:
                if re.search(pattern, code):
                    hits.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    assert not hits, "\n".join(hits)


def test_only_save_qr_writes_files():
    writers = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if "write_bytes" in line.split("#")[0]:
                writers.append(path.name)
    # The two write_bytes calls are the PNG/SVG export in qr_service.save_qr,
    # which holds the QR image only, to a path the user picked.
    assert writers == ["qr_service.py", "qr_service.py"]


def test_runtime_run_leaves_no_trace(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "privacy-check.py")],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
