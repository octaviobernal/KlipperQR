#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Runtime privacy check (issue #31).

Runs the real window offscreen with private XDG folders, then copies a unique
marker text, reads it, generates the QR code, saves it, clears, and closes.
Fails (exit 1) if the marker shows up in anything the app printed, or in any
file under the temporary data/config/cache/state/runtime folders.

Usage: python3 scripts/privacy-check.py   (run it from anywhere)
The marker is a made-up string, never real clipboard content.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "PRIVACY-MARKER-7f3a9c1e-do-not-leak"

CHILD = r"""
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ["KQR_SRC"])
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from klipperqr.main import QML_MAIN, expose_services

app = QGuiApplication([])
app.setApplicationName("KlipperQR")
engine = QQmlApplicationEngine()
clipboard_service, qr_service = expose_services(engine)
engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
window = engine.rootObjects()[0]
window.show()
QTest.qWait(300)
app.clipboard().setText(os.environ["KQR_MARKER"])
clipboard_service.read()                      # copy -> read
qr_service.generate(clipboard_service.text)   # generate
out = Path(os.environ["KQR_OUT"])
assert qr_service.saveToFile(QUrl.fromLocalFile(str(out / "qrcode.png")), "png")
assert qr_service.saveToFile(QUrl.fromLocalFile(str(out / "qrcode.svg")), "svg")
from PySide6.QtCore import QMetaObject, Qt
QMetaObject.invokeMethod(window, "clearAll", Qt.ConnectionType.DirectConnection)
QTest.qWait(200)
assert qr_service.state == 1 and clipboard_service.text == ""
window.close()
QTest.qWait(100)
"""


def main() -> int:
    marker = MARKER.encode()
    with tempfile.TemporaryDirectory(prefix="kqr-privacy-") as tmp:
        base = Path(tmp)
        homes = {
            "XDG_DATA_HOME": base / "data",
            "XDG_CONFIG_HOME": base / "config",
            "XDG_CACHE_HOME": base / "cache",
            "XDG_STATE_HOME": base / "state",
            "XDG_RUNTIME_DIR": base / "run",
            "HOME": base / "home",
        }
        out = base / "saved"
        for path in [*homes.values(), out]:
            path.mkdir(parents=True)
        os.chmod(homes["XDG_RUNTIME_DIR"], 0o700)
        env = {k: str(v) for k, v in homes.items()}
        env.update(
            PATH=os.environ.get("PATH", ""),
            QT_QPA_PLATFORM="offscreen",
            KQR_SRC=str(ROOT / "src"),
            KQR_MARKER=MARKER,
            KQR_OUT=str(out),
            QT_LOGGING_RULES="*.debug=true",  # most verbose Qt output
            QML_IMPORT_PATH=os.environ.get("QML_IMPORT_PATH", ""),
            QT_PLUGIN_PATH=os.environ.get("QT_PLUGIN_PATH", ""),
            LD_LIBRARY_PATH=os.environ.get("LD_LIBRARY_PATH", ""),
        )
        proc = subprocess.run(
            [sys.executable, "-I", "-c", CHILD],
            env=env,
            capture_output=True,
            timeout=120,
            cwd=base,
        )
        failures = []
        if proc.returncode != 0:
            failures.append(
                "driver failed (%d): %s"
                % (proc.returncode, proc.stderr.decode()[-800:])
            )
        if marker in proc.stdout or marker in proc.stderr:
            failures.append("marker found in the program output")
        # Saved files are the user's explicit export: only the QR image, never
        # the text. They live outside the app folders.
        for folder in homes.values():
            for f in folder.rglob("*"):
                if f.is_file() and marker in f.read_bytes():
                    failures.append("marker found in file: %s" % f.relative_to(base))
        for f in out.iterdir():
            if marker in f.read_bytes():
                failures.append("marker found in saved file: %s" % f.name)
        print("output bytes checked: %d" % (len(proc.stdout) + len(proc.stderr)))
        for fail in failures:
            print("FAIL:", fail)
        if not failures:
            print("OK: no trace of the marker in output or app folders")
        return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
