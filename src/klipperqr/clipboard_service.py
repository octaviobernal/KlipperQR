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

Refocus rules (issue #41), implemented only here; the UI just reacts:

* read()       explicit read (Paste button). Also resets the last-read marker
               unless the result is text. Always gives a full result:
               state/text/message are updated, outcome is EXPLICIT.
* autoRead()   read on window focus. Compares with the previous text read and
               only touches state/text when the text is NEW. Unchanged text,
               an empty or non-text clipboard, a failed read and the app's own
               clipboard changes leave state/text exactly as they were, so a
               binding on them can never wipe the QR or the user's edits.
* markOwnChange()  call right AFTER the app put something on the clipboard
               (e.g. Copy image); autoRead() then ignores that content. This
               only matters if that content includes text; pure images are
               already ignored as "not text".
* clear()      empties state/text but KEEPS the last-read marker, so the same
               clipboard text does not come back on the next focus (Clear, #26).
* forgetLastRead()  drops the marker, so the same text counts as new again.

The "last read" marker and the own-change marker are SHA-256 digests held in
memory only; no clipboard text is stored for the comparison.
"""

import hashlib
from enum import IntEnum

from PySide6.QtCore import (
    Property,
    QByteArray,
    QEnum,
    QMimeData,
    QObject,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication, QImage, QWindow
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

    @QEnum
    class Outcome(IntEnum):
        NONE = 0  # no read yet
        EXPLICIT = 1  # explicit read: show state/text/message as they are
        NEW_TEXT = 2  # automatic read found different text: replace the UI text
        UNCHANGED = 3  # automatic read, same text as before: do nothing
        IGNORED = 4  # automatic read, empty/not text/failed/own change: do nothing

    stateChanged = Signal()
    outcomeChanged = Signal()
    # Emitted after every read with the Outcome value (also if it did not change).
    readFinished = Signal(int)
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
        self._outcome = ClipboardService.Outcome.NONE
        self._last_digest = None  # digest of the text of the previous text read
        self._own_digest = None  # digest of clipboard content the app set itself

    def __repr__(self) -> str:
        # Never include the text.
        return f"ClipboardService(state={self._state.name})"

    # --- properties -------------------------------------------------------

    @Property(int, notify=stateChanged)
    def state(self) -> int:
        return int(self._state)

    @Property(int, notify=outcomeChanged)
    def outcome(self) -> int:
        """Outcome of the most recent read (see the Outcome enum)."""
        return int(self._outcome)

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
        """Explicit read (Paste). Always a full result, even if unchanged."""
        Outcome = ClipboardService.Outcome
        state, text, _mime = self._fetch()
        # What the user sees after this read is the marker. Only text has a
        # digest; for empty/not-text/failed the old digest no longer matches
        # what is shown, so the same text must count as new next time.
        self._last_digest = (
            _digest(text) if state == ClipboardService.State.TEXT else None
        )
        self._own_digest = None
        self._set_result(state, text)
        self._set_outcome(Outcome.EXPLICIT)

    @Slot()
    def autoRead(self) -> None:  # noqa: N802 - QML-visible name
        """Read on window focus. Only replaces state/text when the text is new."""
        Outcome = ClipboardService.Outcome
        State = ClipboardService.State
        state, text, mime = self._fetch()
        if self._own_digest is not None:
            if _mime_digest(mime) == self._own_digest:
                self._set_outcome(Outcome.IGNORED)
                return
            self._own_digest = None  # something else is on the clipboard now
        if state != State.TEXT:
            self._set_outcome(Outcome.IGNORED)
            return
        digest = _digest(text)
        if digest == self._last_digest:
            self._set_outcome(Outcome.UNCHANGED)
            return
        self._last_digest = digest
        self._set_result(state, text)
        self._set_outcome(Outcome.NEW_TEXT)

    @Slot()
    def markOwnChange(self) -> None:  # noqa: N802
        """Call right after the app put data on the clipboard.

        The next autoRead() that still sees exactly this content is ignored.
        Different content (copied elsewhere later) is handled normally.
        """
        try:
            clipboard = self._clipboard
            if clipboard is None:
                clipboard = QGuiApplication.clipboard()
            self._own_digest = _mime_digest(clipboard.mimeData())
        except Exception:  # noqa: BLE001 - deliberately drop the details
            self._own_digest = None

    @Slot(QByteArray, result=bool)
    def copyImage(self, png) -> bool:  # noqa: N802 - QML-visible name
        """Put a PNG image on the clipboard (Copy image, #27).

        Returns True on success and False if the data is not a valid image or
        the clipboard cannot be written. Never raises and never logs. On
        success the change is marked as the app's own (markOwnChange), so
        regaining focus does not react to it. Needs no Flatpak permission.
        """
        try:
            image = QImage.fromData(QByteArray(png), "PNG")
            if image.isNull():
                return False
            clipboard = self._clipboard
            if clipboard is None:
                clipboard = QGuiApplication.clipboard()
            mime = QMimeData()
            mime.setImageData(image)
            clipboard.setMimeData(mime)  # the clipboard takes ownership
        except Exception:  # noqa: BLE001 - deliberately drop the details
            return False
        self.markOwnChange()
        return True

    @Slot()
    def clear(self) -> None:
        """Forget the shown text/state but keep the last-read marker."""
        self._set_result(ClipboardService.State.NOT_READ, "")
        self._set_outcome(ClipboardService.Outcome.NONE)

    @Slot()
    def forgetLastRead(self) -> None:  # noqa: N802
        """Drop the last-read marker: the same text counts as new next time."""
        self._last_digest = None

    def _fetch(self):
        """Return (state, text, mime) from the clipboard. Never raises."""
        State = ClipboardService.State
        text = ""
        mime = None
        try:
            clipboard = self._clipboard
            if clipboard is None:
                clipboard = QGuiApplication.clipboard()
            mime = clipboard.mimeData()
            if mime is None:
                state = State.EMPTY
            elif mime.hasText():
                text = mime.text()
                state = State.TEXT if text else State.EMPTY
            elif mime.formats():
                state = State.NOT_TEXT
            else:
                state = State.EMPTY
        except Exception:  # noqa: BLE001 - deliberately drop the details
            text = ""
            mime = None
            state = State.FAILED
        return state, text, mime

    def attach_window(self, window: QWindow) -> None:
        """Read whenever `window` becomes the active (focused) window."""
        window.activeChanged.connect(lambda: self._on_active_changed(window))
        if window.isActive():  # already focused: no activeChanged will come
            self.autoRead()

    def _on_active_changed(self, window: QWindow) -> None:
        if window.isActive():
            self.autoRead()

    # --- internals --------------------------------------------------------

    def _set_outcome(self, outcome: "ClipboardService.Outcome") -> None:
        changed = outcome != self._outcome
        self._outcome = outcome
        if changed:
            self.outcomeChanged.emit()
        self.readFinished.emit(int(outcome))

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


def _digest(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).digest()


def _mime_digest(mime) -> bytes | None:
    """Digest of all formats and their bytes; None if nothing to compare."""
    if mime is None:
        return None
    h = hashlib.sha256()
    for fmt in sorted(mime.formats()):
        h.update(fmt.encode("utf-8"))
        h.update(bytes(mime.data(fmt)))
    # Image formats such as application/x-qt-image expose 0 bytes through
    # data(), so also hash the pixels (in memory only, no copy is kept).
    try:
        if mime.hasImage():
            image = mime.imageData()
            if hasattr(image, "constBits"):
                h.update(
                    f"{image.width()}x{image.height()}:{image.format().name}".encode()
                )
                h.update(image.constBits().tobytes())
    except Exception:  # noqa: BLE001 - digest still covers the formats
        pass
    return h.digest()
