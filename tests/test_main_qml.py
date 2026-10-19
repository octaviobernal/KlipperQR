# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Load qml/Main.qml offscreen (like CI) and fail on any QML error or warning."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QObject, QUrl, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

from klipperqr.main import QML_MAIN, expose_services  # noqa: E402


def test_main_qml_loads_without_errors():
    app = QGuiApplication.instance() or QGuiApplication([])
    messages = []
    previous = qInstallMessageHandler(lambda mode, ctx, msg: messages.append(msg))
    try:
        engine = QQmlApplicationEngine()
        services = expose_services(engine)  # noqa: F841
        engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
        roots = engine.rootObjects()
        assert roots, "Main.qml failed to load:\n" + "\n".join(messages)
        window = roots[0]
        window.show()
        app.processEvents()
        assert window.property("title") == "KlipperQR"
        assert window.property("hasText") is False
        assert window.property("minimumWidth") > 0
        # Exposed clipboard state follows the Python service.
        clipboard_service = services[0]
        assert window.property("clipboardState") == clipboard_service.state
        # Let the toolbar (Paste action) finish creating its items before closing.
        from PySide6.QtTest import QTest

        QTest.qWait(300)
        window.close()
    finally:
        qInstallMessageHandler(previous)
    # Known environment noise: with the pip PySide6 + system Kirigami used in
    # development, ANY Kirigami page that has an action logs these two lines
    # (reproduced with a 6-line Kirigami.Page, not specific to this app).
    benign = (
        "ActionToolBar.qml: Object or context destroyed",
        "Could not create delegate for ToolBarLayout",
    )
    errors = [
        m
        for m in messages
        if ("Main.qml" in m or "qml" in m.lower()) and not any(b in m for b in benign)
    ]
    assert not errors, "\n".join(errors)


def _find_image(window):
    from PySide6.QtQuick import QQuickItem

    for item in window.findChildren(QQuickItem):
        if item.metaObject().className().startswith("QQuickImage") and (
            item.property("source").toString().startswith("data:image/png")
        ):
            return item
    return None


def test_qr_card_follows_text_and_problems():
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    clipboard_service, qr_service = expose_services(engine)
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    window = engine.rootObjects()[0]
    window.show()
    clipboard = app.clipboard()

    def settle():
        for _ in range(5):
            app.processEvents()

    # Text: a QR code with an accessible name and description appears.
    clipboard.setText("https://kde.org")
    clipboard_service.read()
    settle()
    assert window.property("showQr") is True
    image = _find_image(window)
    assert image is not None
    first = image.property("source").toString()

    # Different text: different image.
    clipboard.setText("something else")
    clipboard_service.read()
    settle()
    assert _find_image(window).property("source").toString() != first

    # Too long: no QR, plain message.
    clipboard.setText("x" * 5000)
    clipboard_service.read()
    settle()
    assert window.property("showQr") is False
    assert _find_image(window) is None or not _find_image(window).isVisible()
    assert "too long" in window.property("problemExplanation")

    # Clearing the text removes the code.
    clipboard_service.clear()
    settle()
    assert window.property("showQr") is False
    assert qr_service.pngDataUrl == ""
    window.close()


def _setup_with_fake_clipboard():
    from PySide6.QtCore import QMimeData

    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    clipboard_service, qr_service = expose_services(engine)

    class Fake:
        mime = QMimeData()

        def mimeData(self):  # noqa: N802 - Qt naming
            return self.mime

    fake = Fake()
    clipboard_service._clipboard = fake

    def put(text):
        mime = QMimeData()
        if text is not None:
            mime.setText(text)
        fake.mime = mime

    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    window = engine.rootObjects()[0]
    window.show()
    field = window.findChild(QObject, "encodedTextField")
    assert field is not None
    return app, engine, window, field, clipboard_service, qr_service, put


def test_text_field_shows_clipboard_and_updates_qr_when_typing():
    from PySide6.QtTest import QTest

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    assert field.property("text") == ""
    assert window.property("showQr") is False  # empty state

    put("https://kde.org")
    cs.read()
    app.processEvents()
    assert field.property("text") == "https://kde.org"
    assert window.property("encodedText") == "https://kde.org"
    assert window.property("showQr") is True
    first = qr.pngDataUrl

    # Typing: the QR follows after the short delay, without a button.
    field.setProperty("text", "typed text")
    QTest.qWait(600)
    assert window.property("encodedText") == "typed text"
    assert qr.pngDataUrl != first

    # A 1000-character text is handled in well under a second.
    import time

    start = time.monotonic()
    field.setProperty("text", "a" * 1000)
    QTest.qWait(600)
    assert window.property("showQr") is True
    assert time.monotonic() - start < 2

    # Empty field: back to the empty state.
    field.setProperty("text", "")
    QTest.qWait(600)
    assert window.property("showQr") is False
    assert window.property("problemTitle") == "No text to encode"
    window.close()


def test_refocus_replaces_edits_only_for_changed_clipboard_text():
    from PySide6.QtTest import QTest

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    put("original")
    cs.autoRead()
    app.processEvents()
    assert field.property("text") == "original"

    field.setProperty("text", "my edit")
    QTest.qWait(600)

    # Unchanged, empty and not-text clipboards leave the edit alone.
    cs.autoRead()
    put("")
    cs.autoRead()
    put(None)
    cs.autoRead()
    app.processEvents()
    assert field.property("text") == "my edit"
    assert window.property("encodedText") == "my edit"

    # Changed clipboard text replaces it.
    put("new clipboard text")
    cs.autoRead()
    app.processEvents()
    assert field.property("text") == "new clipboard text"
    assert window.property("encodedText") == "new clipboard text"

    # An explicit Paste always restores the clipboard text.
    field.setProperty("text", "edited again")
    QTest.qWait(600)
    cs.read()
    app.processEvents()
    assert field.property("text") == "new clipboard text"
    window.close()


def test_paste_action_always_shows_result_and_hint():
    from PySide6.QtCore import QMetaObject, Qt

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    action = window.findChild(QObject, "pasteAction")
    assert action is not None
    assert "Ctrl+Shift+V" in action.property("tooltip")
    assert action.property("shortcut") == "Ctrl+Shift+V"

    def paste():
        QMetaObject.invokeMethod(action, "trigger", Qt.DirectConnection)
        app.processEvents()

    # Empty state shows the limits hint.
    assert "only read the clipboard while this window is active" in window.property(
        "problemExplanation"
    )

    put("hello")
    paste()
    assert field.property("text") == "hello"
    assert window.property("showQr") is True

    # Unchanged text but edited field: Paste still restores it.
    field.setProperty("text", "edited")
    app.processEvents()
    paste()
    assert field.property("text") == "hello"

    # Empty clipboard: friendly message, no stale QR.
    put(None)
    paste()
    assert window.property("showQr") is False
    explanation = window.property("problemExplanation")
    assert "clipboard is empty" in explanation
    assert "press Paste" in explanation

    # Automatic read of the same state does not wipe an existing QR.
    put("again")
    paste()
    assert window.property("showQr") is True
    put(None)
    cs.autoRead()
    app.processEvents()
    assert window.property("showQr") is True
    window.close()


def test_clear_action_empties_text_and_qr_without_resurrecting_it():
    from PySide6.QtCore import QMetaObject, Qt

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    action = window.findChild(QObject, "clearAction")
    assert action is not None
    assert action.property("text") == "Clear"
    assert "Ctrl+Shift+Delete" in action.property("tooltip")
    assert action.property("shortcut") == "Ctrl+Shift+Delete"
    # Nothing to clear yet: disabled.
    assert action.property("enabled") is False

    put("secret token")
    cs.autoRead()
    app.processEvents()
    assert window.property("showQr") is True
    assert action.property("enabled") is True

    QMetaObject.invokeMethod(action, "trigger", Qt.DirectConnection)
    app.processEvents()
    assert field.property("text") == ""
    assert window.property("encodedText") == ""
    assert window.property("showQr") is False
    assert window.property("problemTitle") == "No text to encode"
    assert action.property("enabled") is False
    # Services keep no text in memory.
    assert cs.text == ""
    assert qr.pngDataUrl == ""
    assert qr.svg == ""

    # Regaining focus with the same clipboard text does not bring it back.
    cs.autoRead()
    app.processEvents()
    assert field.property("text") == ""
    assert window.property("showQr") is False

    # Changed clipboard text is shown.
    put("another")
    cs.autoRead()
    app.processEvents()
    assert field.property("text") == "another"

    # Clear, then Paste restores the old clipboard text.
    QMetaObject.invokeMethod(action, "trigger", Qt.DirectConnection)
    app.processEvents()
    cs.read()
    app.processEvents()
    assert field.property("text") == "another"
    window.close()


def test_copy_image_action_copies_png_and_keeps_text():
    from PySide6.QtCore import QMetaObject, QMimeData, Qt

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    fake = cs._clipboard
    fake.setMimeData = lambda mime: setattr(fake, "mime", mime)
    action = window.findChild(QObject, "copyImageAction")
    assert action is not None
    assert action.property("text") == "Copy image"
    assert "Ctrl+Shift+C" in action.property("tooltip")
    assert action.property("shortcut") == "Ctrl+Shift+C"
    # No QR yet: disabled, no message.
    assert action.property("enabled") is False
    assert window.findChild(QObject, "copyMessage").property("visible") is False

    put("hello")
    cs.autoRead()
    app.processEvents()
    assert action.property("enabled") is True

    QMetaObject.invokeMethod(action, "trigger", Qt.DirectConnection)
    app.processEvents()
    assert fake.mime.hasImage()
    assert fake.mime.imageData().width() > 0
    assert window.findChild(QObject, "copyMessage").property("visible") is True
    assert window.property("copyResult") is True

    # Regaining focus: text and QR stay, no not-text message.
    cs.autoRead()
    app.processEvents()
    assert field.property("text") == "hello"
    assert window.property("showQr") is True

    # A failing clipboard shows a friendly error.
    def broken(mime):
        raise RuntimeError("no")

    fake.setMimeData = broken
    QMetaObject.invokeMethod(action, "trigger", Qt.DirectConnection)
    app.processEvents()
    assert window.property("copyResult") is False
    assert "Could not copy" in window.findChild(QObject, "copyMessage").property("text")
    assert isinstance(fake.mime, QMimeData)
    window.close()
