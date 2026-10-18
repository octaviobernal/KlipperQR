# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Clipboard service: the only place in KlipperQR that touches the clipboard.

Decision and limits: docs/clipboard.md. In short, the text is read with Qt's
QClipboard on the UI thread, only on an explicit call to read() and when the
window becomes active. This is NOT background monitoring: on Wayland the read
returns nothing while the window is not focused.

Privacy (see CONTRIBUTING.md): the clipboard text is kept in memory only. It is
never logged, written to disk, stored in settings or sent anywhere, and it
never appears in an exception message or in repr(). There is deliberately no
logging in this module.
"""

from enum import IntEnum

from PySide6.QtCore import (
    Property,
    QEnum,
    QObject,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QmlElement, QmlUncreatable

# Registers the type for QML as `import KlipperQR` so QML can write
# ClipboardService.State.TEXT. The registration happens when this module is
# imported, so it must be imported before the QML engine loads. The instance
# itself is still exposed as the context property `clipboardService`.
QML_IMPORT_NAME = "KlipperQR"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Use the clipboardService instance provided by the application.")
class ClipboardService(QObject):
    """Reads clipboard text on demand and when the attached window is activated."""

    @QEnum
    class State(IntEnum):
        NOT_READ = 0  # nothing read yet
        TEXT = 1  # text available in `text`
        EMPTY = 2  # clipboard empty (or not readable because unfocused)
        NOT_TEXT = 3  # clipboard holds something else, e.g. an image
        FAILED = 4  # the read itself failed

    stateChanged = Signal()
    textChanged = Signal()
    messageChanged = Signal()

    def __init__(self, clipboard=None, parent=None):
        """`clipboard` is anything with a `mimeData()` method (QClipboard or a fake).

        Defaults to the application clipboard (needs a QGuiApplication).
        """
        super().__init__(parent)
        self._clipboard = clipboard
        self._state = ClipboardService.State.NOT_READ
        self._text = ""

    def __repr__(self) -> str:
        # Never include the text.
        return f"ClipboardService(state={self._state.name})"

    # --- properties -------------------------------------------------------

    @Property(int, notify=stateChanged)
    def state(self) -> int:
        return int(self._state)

    @Property(str, notify=textChanged)
    def text(self) -> str:
        return self._text

    @Property(str, notify=messageChanged)
    def message(self) -> str:
        """Friendly, translatable text for the current non-text state."""
        State = ClipboardService.State
        if self._state == State.EMPTY:
            return self.tr("The clipboard is empty or cannot be read right now.")
        if self._state == State.NOT_TEXT:
            return self.tr("The clipboard does not contain text.")
        if self._state == State.FAILED:
            return self.tr("Could not read the clipboard.")
        return ""

    # --- actions ----------------------------------------------------------

    @Slot()
    def read(self) -> None:
        """Read the clipboard now. Never raises; the result is in `state`."""
        State = ClipboardService.State
        text = ""
        try:
            clipboard = self._clipboard
            if clipboard is None:
                clipboard = QGuiApplication.clipboard()
            mime = clipboard.mimeData()
            if mime is None:
                new_state = State.EMPTY
            elif mime.hasText():
                text = mime.text()
                new_state = State.TEXT if text else State.EMPTY
            elif mime.formats():
                new_state = State.NOT_TEXT
            else:
                new_state = State.EMPTY
        except Exception:  # noqa: BLE001 - deliberately drop the details
            text = ""
            new_state = State.FAILED
        self._set_result(new_state, text)

    def attach_window(self, window: QWindow) -> None:
        """Read whenever `window` becomes the active (focused) window."""
        window.activeChanged.connect(lambda: self._on_active_changed(window))
        if window.isActive():  # already focused: no activeChanged will come
            self.read()

    def _on_active_changed(self, window: QWindow) -> None:
        if window.isActive():
            self.read()

    # --- internals --------------------------------------------------------

    def _set_result(self, state: "ClipboardService.State", text: str) -> None:
        old_message = self.message
        if state != self._state:
            self._state = state
            self.stateChanged.emit()
        if text != self._text:
            self._text = text
            self.textChanged.emit()
        if self.message != old_message:
            self.messageChanged.emit()
