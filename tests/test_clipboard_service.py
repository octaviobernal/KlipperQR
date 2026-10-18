# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402
from PySide6.QtCore import QMimeData  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QWindow  # noqa: E402

from klipperqr.clipboard_service import ClipboardService  # noqa: E402

State = ClipboardService.State
SECRET = "secret-test-text-4711"


@pytest.fixture(scope="module")
def app():
    return QGuiApplication.instance() or QGuiApplication([])


class FakeClipboard:
    """Stands in for QClipboard: only mimeData() is needed."""

    def __init__(self, mime=None, error=None):
        self.mime = mime
        self.error = error

    def mimeData(self):  # noqa: N802 - Qt naming
        if self.error:
            raise self.error
        return self.mime


def text_mime(text):
    mime = QMimeData()
    mime.setText(text)
    return mime


def test_initial_state(app):
    service = ClipboardService(FakeClipboard())
    assert service.state == State.NOT_READ
    assert service.text == ""


def test_read_text(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    service.read()
    assert service.state == State.TEXT
    assert service.text == SECRET
    assert service.message == ""


def test_read_empty(app):
    for mime in (None, QMimeData(), text_mime("")):
        service = ClipboardService(FakeClipboard(mime))
        service.read()
        assert service.state == State.EMPTY
        assert service.text == ""
        assert service.message


def test_read_non_text(app):
    mime = QMimeData()
    mime.setImageData(QImage(4, 4, QImage.Format.Format_RGB32))
    service = ClipboardService(FakeClipboard(mime))
    service.read()
    assert service.state == State.NOT_TEXT
    assert service.text == ""
    assert service.message


def test_failed_read_does_not_raise_or_leak(app):
    service = ClipboardService(FakeClipboard(error=RuntimeError(SECRET)))
    service.read()
    assert service.state == State.FAILED
    assert service.text == ""
    assert service.message
    assert SECRET not in service.message


def test_states_are_distinct_messages(app):
    messages = set()
    image = QMimeData()
    image.setImageData(QImage(2, 2, QImage.Format.Format_RGB32))
    for fake in (
        FakeClipboard(QMimeData()),
        FakeClipboard(image),
        FakeClipboard(error=OSError()),
    ):
        service = ClipboardService(fake)
        service.read()
        messages.add(service.message)
    assert len(messages) == 3


def test_text_is_cleared_when_clipboard_becomes_empty(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.read()
    fake.mime = QMimeData()
    service.read()
    assert service.state == State.EMPTY
    assert service.text == ""


def test_signals_emitted_only_on_change(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    states, texts = [], []
    service.stateChanged.connect(lambda: states.append(1))
    service.textChanged.connect(lambda: texts.append(1))
    service.read()
    service.read()
    assert len(states) == 1
    assert len(texts) == 1


def test_focus_triggers_read(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    window = QWindow()
    service.attach_window(window)
    # Simulate focus gain/loss by calling the handler the signal is wired to.
    window.activeChanged.emit()
    assert service.state == State.NOT_READ  # window not active: no read
    window.show()
    window.requestActivate()
    app.processEvents()
    if not window.isActive():
        pytest.skip("offscreen platform did not activate the window")
    assert service.state == State.TEXT
    assert service.text == SECRET


def test_active_handler_reads_only_when_active(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))

    class StubWindow:
        active = False

        def isActive(self):  # noqa: N802
            return self.active

    win = StubWindow()
    service._on_active_changed(win)
    assert service.state == State.NOT_READ
    win.active = True
    service._on_active_changed(win)
    assert service.state == State.TEXT


def test_no_log_record_contains_text(app, caplog):
    caplog.set_level(logging.DEBUG)
    for fake in (
        FakeClipboard(text_mime(SECRET)),
        FakeClipboard(error=RuntimeError(SECRET)),
    ):
        service = ClipboardService(fake)
        service.read()
        assert SECRET not in repr(service)
    assert all(SECRET not in r.getMessage() for r in caplog.records)
    assert SECRET not in caplog.text


def test_module_has_no_dbus_logging_or_disk_use():
    source = (ROOT / "src" / "klipperqr" / "clipboard_service.py").read_text()
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    imports = [ln for ln in code.splitlines() if ln.startswith(("import", "from"))]
    joined = "\n".join(imports)
    for forbidden in ("QtDBus", "dbus", "QSettings", "logging"):
        assert forbidden not in joined
    assert "print(" not in code
