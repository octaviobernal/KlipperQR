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

from klipperqr.clipboard_service import ClipboardService, _mime_digest  # noqa: E402

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


class ActiveStubWindow:
    """Minimal window stand-in that is already active."""

    class _Signal:
        def connect(self, slot):
            self.slot = slot

    def __init__(self):
        self.activeChanged = self._Signal()

    def isActive(self):  # noqa: N802 - Qt naming
        return True


def test_attach_window_already_active_reads_immediately(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    service.attach_window(ActiveStubWindow())
    assert service.state == State.TEXT


def test_enum_values_resolve_in_qml(app):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    engine = QQmlEngine()
    qml = b"""
import QtQuick
import KlipperQR
QtObject {
    property int viaState: ClipboardService.State.TEXT
    property int viaShort: ClipboardService.TEXT
    property bool defined: ClipboardService.State.FAILED !== undefined
}
"""
    component = QQmlComponent(engine)
    component.setData(qml, QUrl("inline.qml"))
    obj = component.create()
    assert obj is not None, component.errorString()
    assert obj.property("viaState") == 1
    assert obj.property("viaShort") == 1
    assert obj.property("defined") is True


# --- issue #41: unchanged text, own changes, explicit vs automatic reads ----

Outcome = ClipboardService.Outcome
OTHER = "other-test-text-0815"


def image_mime(color=0):
    mime = QMimeData()
    image = QImage(4, 4, QImage.Format.Format_RGB32)
    image.fill(color)
    mime.setImageData(image)
    return mime


def test_auto_read_same_text_twice_is_unchanged(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    service.autoRead()
    assert service.outcome == Outcome.NEW_TEXT
    texts = []
    service.textChanged.connect(lambda: texts.append(1))
    service.autoRead()
    assert service.outcome == Outcome.UNCHANGED
    assert service.state == State.TEXT
    assert service.text == SECRET
    assert texts == []


def test_auto_read_different_text_is_new(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = text_mime(OTHER)
    service.autoRead()
    assert service.outcome == Outcome.NEW_TEXT
    assert service.text == OTHER


def test_auto_read_empty_after_text_keeps_text(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    for mime in (QMimeData(), None, text_mime("")):
        fake.mime = mime
        service.autoRead()
        assert service.outcome == Outcome.IGNORED
        assert service.state == State.TEXT
        assert service.text == SECRET


def test_auto_read_image_after_text_keeps_text(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = image_mime()
    service.autoRead()
    assert service.outcome == Outcome.IGNORED
    assert service.state == State.TEXT
    assert service.text == SECRET


def test_auto_read_failure_keeps_text(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.error = RuntimeError(SECRET)
    service.autoRead()
    assert service.outcome == Outcome.IGNORED
    assert service.state == State.TEXT
    assert service.text == SECRET


def test_same_text_after_image_is_still_unchanged(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = image_mime()
    service.autoRead()
    fake.mime = text_mime(SECRET)
    service.autoRead()
    assert service.outcome == Outcome.UNCHANGED


def test_own_change_is_ignored(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = image_mime(0xFFFFFF)  # the app "copies its QR image"
    service.markOwnChange()
    service.autoRead()
    service.autoRead()
    assert service.outcome == Outcome.IGNORED
    assert service.state == State.TEXT
    assert service.text == SECRET


def test_own_change_then_other_copy_is_handled(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = image_mime(0xFFFFFF)
    service.markOwnChange()
    fake.mime = text_mime(OTHER)  # user copies something else later
    service.autoRead()
    assert service.outcome == Outcome.NEW_TEXT
    assert service.text == OTHER


def test_own_change_then_foreign_image_is_ignored_but_not_hidden(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = image_mime(0xFFFFFF)
    service.markOwnChange()
    fake.mime = image_mime(0x000000)
    service.autoRead()
    assert service.outcome == Outcome.IGNORED  # not text: still never replaces
    assert service.text == SECRET


def test_explicit_read_after_unchanged_text_gives_full_result(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    service.autoRead()
    results = []
    service.readFinished.connect(results.append)
    service.read()
    assert results == [Outcome.EXPLICIT]
    assert service.state == State.TEXT
    assert service.text == SECRET


def test_explicit_read_reports_empty_and_not_text(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = QMimeData()
    service.read()
    assert (service.outcome, service.state) == (Outcome.EXPLICIT, State.EMPTY)
    assert service.text == "" and service.message
    fake.mime = image_mime()
    service.read()
    assert (service.outcome, service.state) == (Outcome.EXPLICIT, State.NOT_TEXT)


def test_explicit_read_of_own_change_still_reports_not_text(app):
    fake = FakeClipboard(image_mime())
    service = ClipboardService(fake)
    service.markOwnChange()
    service.read()
    assert service.state == State.NOT_TEXT


def test_clear_keeps_marker_so_same_text_is_not_new(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    service.autoRead()
    service.clear()
    assert service.state == State.NOT_READ
    assert service.text == ""
    service.autoRead()
    assert service.outcome == Outcome.UNCHANGED
    assert service.text == ""
    service.read()  # only an explicit Paste brings it back
    assert service.text == SECRET


def test_clear_then_changed_text_is_new(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    service.clear()
    fake.mime = text_mime(OTHER)
    service.autoRead()
    assert service.outcome == Outcome.NEW_TEXT
    assert service.text == OTHER


def test_forget_last_read_makes_same_text_new(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    service.autoRead()
    service.forgetLastRead()
    service.autoRead()
    assert service.outcome == Outcome.NEW_TEXT


def test_no_plain_text_kept_for_comparison(app):
    service = ClipboardService(FakeClipboard(text_mime(SECRET)))
    service.autoRead()
    service.markOwnChange()
    held = [v for v in vars(service).values() if isinstance(v, (str, bytes))]
    assert held.count(SECRET) == 1  # only `_text` (the shown text)
    assert service._last_digest != SECRET.encode()
    assert SECRET not in repr(service)


def test_outcome_enum_resolves_in_qml(app):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.setData(
        b"import QtQuick\nimport KlipperQR\n"
        b"QtObject { property int a: ClipboardService.Outcome.NEW_TEXT }",
        QUrl("inline.qml"),
    )
    obj = component.create()
    assert obj is not None, component.errorString()
    assert obj.property("a") == Outcome.NEW_TEXT


# --- review fixes for #41 -----------------------------------------------------


def text_and_image_mime(text, color=0xFFFFFF):
    """Own content that includes text, like Copy image on some platforms."""
    mime = image_mime(color)
    mime.setText(text)
    return mime


def test_text_comes_back_after_empty_explicit_read(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()  # (1) sees the text
    fake.mime = QMimeData()
    service.read()  # (2) cleared elsewhere, Paste shows the empty message
    assert service.state == State.EMPTY
    fake.mime = text_mime(SECRET)  # (3) copied again
    service.autoRead()  # (4) refocus must show it
    assert service.outcome == Outcome.NEW_TEXT
    assert service.state == State.TEXT
    assert service.text == SECRET


def test_text_comes_back_after_not_text_or_failed_explicit_read(app):
    for bad in (image_mime(), RuntimeError(SECRET)):
        fake = FakeClipboard(text_mime(SECRET))
        service = ClipboardService(fake)
        service.autoRead()
        if isinstance(bad, Exception):
            fake.error = bad
        else:
            fake.mime = bad
        service.read()
        assert service.state in (State.NOT_TEXT, State.FAILED)
        fake.error = None
        fake.mime = text_mime(SECRET)
        service.autoRead()
        assert service.outcome == Outcome.NEW_TEXT
        assert service.state == State.TEXT


def test_own_change_with_text_is_ignored_only_when_marked(app):
    results = {}
    for marked in (True, False):
        fake = FakeClipboard(text_mime(SECRET))
        service = ClipboardService(fake)
        service.autoRead()
        fake.mime = text_and_image_mime(OTHER)
        if marked:
            service.markOwnChange()
        service.autoRead()
        results[marked] = (service.outcome, service.text)
    assert results[True] == (Outcome.IGNORED, SECRET)
    assert results[False] == (Outcome.NEW_TEXT, OTHER)


def test_own_change_with_text_and_html_is_ignored_when_marked(app):
    mime = text_mime(OTHER)
    mime.setHtml("<b>x</b>")
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    fake.mime = mime
    service.markOwnChange()
    service.autoRead()
    assert service.outcome == Outcome.IGNORED
    assert service.text == SECRET


def test_own_mark_is_dropped_when_different_content_arrives(app):
    fake = FakeClipboard(text_mime(SECRET))
    service = ClipboardService(fake)
    service.autoRead()
    own = text_and_image_mime(OTHER)
    fake.mime = own
    service.markOwnChange()
    fake.mime = text_mime("third-test-text-42")  # something else arrives
    service.autoRead()
    assert service.outcome == Outcome.NEW_TEXT
    assert service._own_digest is None
    fake.mime = own  # the old own content comes back: no longer protected
    service.autoRead()
    assert service.outcome == Outcome.NEW_TEXT
    assert service.text == OTHER


def test_digest_differs_for_different_images(app):
    black, white = image_mime(0x000000), image_mime(0xFFFFFF)
    assert _mime_digest(black) != _mime_digest(white)
    assert _mime_digest(black) == _mime_digest(image_mime(0x000000))


def test_digest_differs_for_different_images_on_real_clipboard(app):
    clipboard = QGuiApplication.clipboard()
    digests = []
    for color in (0x000000, 0xFFFFFF):
        clipboard.setMimeData(image_mime(color))
        digests.append(_mime_digest(clipboard.mimeData()))
    clipboard.clear()
    assert digests[0] != digests[1]


def test_own_mark_with_real_clipboard_image_plus_text(app):
    clipboard = QGuiApplication.clipboard()
    service = ClipboardService()  # uses the real application clipboard
    clipboard.setMimeData(text_mime(SECRET))
    service.autoRead()
    clipboard.setMimeData(text_and_image_mime(OTHER))
    service.markOwnChange()
    service.autoRead()
    outcome, text = service.outcome, service.text
    clipboard.clear()
    assert (outcome, text) == (Outcome.IGNORED, SECRET)
