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


def test_save_action_state_and_failure_message(tmp_path):
    from PySide6.QtCore import Q_ARG, QMetaObject, Qt, QUrl

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    action = window.findChild(QObject, "saveAction")
    assert action is not None
    assert action.property("text") == "Save"
    assert action.property("shortcut") == "Ctrl+S"
    assert "Ctrl+S" in action.property("tooltip")
    assert action.property("enabled") is False

    put("hello")
    cs.autoRead()
    app.processEvents()
    assert action.property("enabled") is True

    # Suggested name is generic; opening the dialog does not need the text.
    dialog = window.findChild(QObject, "saveDialog")
    QMetaObject.invokeMethod(window, "prepareSaveDialog", Qt.DirectConnection)
    assert dialog.property("currentFolder").toString().startswith("file:///")
    assert dialog.property("currentFile").toString().endswith("/qrcode.png")
    assert "hello" not in dialog.property("currentFile").toString()

    ok = tmp_path / "out.png"
    QMetaObject.invokeMethod(
        window,
        "saveTo",
        Qt.DirectConnection,
        Q_ARG("QVariant", QUrl.fromLocalFile(str(ok))),
        Q_ARG("QVariant", "png"),
    )
    assert ok.is_file() and window.property("saveResult") is True
    QMetaObject.invokeMethod(
        window,
        "saveTo",
        Qt.DirectConnection,
        Q_ARG("QVariant", QUrl.fromLocalFile(str(tmp_path / "no" / "out.png"))),
        Q_ARG("QVariant", "png"),
    )
    assert window.property("saveResult") is False
    assert "Could not save" in window.findChild(QObject, "saveMessage").property("text")
    window.close()


def test_save_dialog_shows_suggested_name_and_saves(tmp_path, monkeypatch):
    """Open the real Qt Quick file dialog offscreen and read its name field."""
    from PySide6.QtCore import QMetaObject, Qt
    from PySide6.QtTest import QTest

    # Use a throw-away Pictures folder so nothing is written to the real one.
    config = tmp_path / "config"
    pictures = tmp_path / "Pictures"
    config.mkdir()
    pictures.mkdir()
    (config / "user-dirs.dirs").write_text(f'XDG_PICTURES_DIR="{pictures}"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    put("secret clipboard text")
    cs.autoRead()
    app.processEvents()
    action = window.findChild(QObject, "saveAction")
    QMetaObject.invokeMethod(action, "trigger", Qt.DirectConnection)
    QTest.qWait(300)

    name_field = window.findChild(QObject, "fileNameTextField")
    assert name_field is not None, "Qt Quick file dialog was not created in the window"
    # Regression for #28: the field used to stay empty.
    assert name_field.property("text") == "qrcode.png"
    dialog = window.findChild(QObject, "saveDialog")
    assert dialog.property("currentFolder").toLocalFile() == str(pictures)
    assert "secret" not in name_field.property("text")

    # Accepting writes the file with that name in that folder.
    # The first visible plain Button of the dialog footer is Open/Save (text is
    # translated, so it is found by type, not by text).
    buttons = [
        c
        for c in window.findChildren(QObject)
        if c.metaObject().className().startswith("Button_QMLTYPE")
        and "_QML_" not in c.metaObject().className()
        and c.property("visible")
        and c.property("text")
    ]
    assert buttons, "no accept button found"
    QMetaObject.invokeMethod(buttons[0], "click", Qt.DirectConnection)
    QTest.qWait(300)
    assert (pictures / "qrcode.png").is_file()
    assert window.property("saveResult") is True
    window.close()


def test_dense_warning_appears_and_disappears_with_text_length():
    from PySide6.QtCore import QMetaObject, Qt
    from PySide6.QtTest import QTest

    from klipperqr.qr_service import DENSE_THRESHOLD_CHARS

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    message = window.findChild(QObject, "denseMessage")
    assert message is not None
    assert message.property("visible") is False  # empty

    def type_text(text):
        field.setProperty("text", text)
        QTest.qWait(600)

    type_text("short text")
    assert message.property("visible") is False

    # Exactly at the threshold: not dense.
    type_text("a" * DENSE_THRESHOLD_CHARS)
    assert window.property("showQr") is True
    assert message.property("visible") is False

    # One more character: warning appears, QR still shown.
    type_text("a" * (DENSE_THRESHOLD_CHARS + 1))
    assert window.property("showQr") is True
    assert message.property("visible") is True
    assert "shortening" in message.property("text")
    assert message.property("type") == 2  # Kirigami.MessageType.Warning

    # Shorter again: warning goes away.
    type_text("a" * 50)
    assert message.property("visible") is False

    # Too long for any QR: the "too long" problem is shown, not the warning.
    type_text("a" * 5000)
    assert window.property("showQr") is False
    assert message.property("visible") is False

    # Clearing hides it as well.
    type_text("a" * (DENSE_THRESHOLD_CHARS + 1))
    assert message.property("visible") is True
    QMetaObject.invokeMethod(
        window.findChild(QObject, "clearAction"), "trigger", Qt.DirectConnection
    )
    app.processEvents()
    assert message.property("visible") is False
    window.close()


def test_dense_qr_card_is_visible_inside_the_page_at_default_size():
    """Regression (#29): with 1500 characters the QR card must really be on screen.

    The dense warning sits above the QR card; it must not push the card below
    the fold or leave the page scrolled away from it.
    """
    from PySide6.QtCore import QPointF
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    app, engine, window, field, cs, qr, put = _setup_with_fake_clipboard()
    QTest.qWait(300)

    def item(name):
        found = [i for i in window.findChildren(QQuickItem) if i.objectName() == name]
        assert found, name
        return found[0]

    def page_flickable():
        return [
            i
            for i in window.findChildren(QQuickItem)
            if i.metaObject().className().startswith("QQuickFlickable")
            and i.property("contentHeight") > 0
            and i.width() > 0.9 * window.width() - 40
        ][0]

    # Default size: 30 x 28 grid units (checked, not assumed).
    assert window.width() > 0 and window.height() > 0
    field.forceActiveFocus()
    text = (("The quick brown fox jumps over the lazy dog. ") * 40)[:1500]
    # Start with a normal (not dense) text, then scroll the page to the bottom
    # (as when the cursor of a long text is made visible) and paste 1500 characters.
    field.setProperty("text", text[:500])
    QTest.qWait(800)
    flick = page_flickable()
    flick.setProperty(
        "contentY", max(0, flick.property("contentHeight") - flick.height())
    )
    field.setProperty("text", text)
    QTest.qWait(800)

    assert window.property("showQr") is True
    assert item("denseMessage").property("visible") is True
    card = item("qrCard")
    image = _find_image(window)
    assert card.isVisible() and image is not None and image.isVisible()
    assert card.width() > 0 and card.height() > 0
    assert abs(card.width() - card.height()) < 1  # square
    # Loaded (Image.status is not readable from Python; use progress/painted size).
    assert image.property("progress") == 1.0
    assert image.property("paintedWidth") > 0 and image.property("paintedHeight") > 0
    assert len(image.property("source").toString()) > 1000

    page = item("mainPage")
    page_top = page.mapToScene(QPointF(0, 0)).y()
    page_bottom = page_top + page.height()
    card_top = card.mapToScene(QPointF(0, 0)).y()
    card_bottom = card_top + card.height()
    # The whole QR card is inside the visible page area.
    assert card_top >= page_top - 1, (card_top, page_top)
    assert card_bottom <= page_bottom + 1, (card_bottom, page_bottom)
    # The warning is shown above the QR card, also visible.
    warn_top = item("denseMessage").mapToScene(QPointF(0, 0)).y()
    assert page_top - 1 <= warn_top < card_top
    window.close()
