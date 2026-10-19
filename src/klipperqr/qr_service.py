# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""QR generator service: turns a text into PNG and SVG data (issue #21).

Library choice and pitfalls: docs/qr-library.md. The settings below are the
ones that document recommends:

* no Micro QR (many phone scanners cannot read it),
* no automatic error-correction boost (the requested level is respected),
* UTF-8 text encoding,
* quiet zone of 4 modules,
* explicit black (#000) modules on a white (#fff) background in BOTH the PNG
  and the SVG, also in dark mode. This is the documented exception to "no
  hardcoded colors" (CONTRIBUTING.md, "QR code colors").

Two layers:

* ``generate_qr(text, level)`` is a plain function returning a ``QrResult``.
  It never raises, whatever the input. Use it from Python code and tests.
* ``QrService`` is the QML-facing object. QML calls ``generate(text)`` and
  binds to ``state``, ``dense``, ``message``, ``png``, ``svg`` and
  ``pngDataUrl`` (a ``data:image/png;base64,...`` string for ``Image.source``;
  it changes with every new code, so nothing old is kept around).

Privacy (see CONTRIBUTING.md): the text is only used to build the symbol. It
is not stored (only the generated image data is kept, in memory, until the
next call), not logged, not written to disk or settings, and never appears in
an exception message, ``repr()`` or a user message. There is deliberately no
logging in this module.

Performance: building a maximum-size symbol takes roughly 0.15 s, which is
acceptable on the UI thread for a clipboard-sized text. If that ever becomes
a problem, move ``generate_qr`` to a worker thread; it is a pure function.
"""

import base64
import io
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

import segno
from PySide6.QtCore import (
    Property,
    QByteArray,
    QCoreApplication,
    QEnum,
    QObject,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtQml import QmlElement, QmlUncreatable

QML_IMPORT_NAME = "KlipperQR"
QML_IMPORT_MAJOR_VERSION = 1

# Texts longer than this many characters give a very dense code that phones
# may struggle to scan (issue #28). PROVISIONAL: to be confirmed by a real
# phone scan; change it here only.
DENSE_THRESHOLD_CHARS = 1000

ERROR_LEVELS = ("L", "M", "Q", "H")
DEFAULT_ERROR_LEVEL = "M"

# Pixels per module in the PNG and the SVG size (sharp when shown at 200%).
SCALE = 10
QUIET_ZONE_MODULES = 4  # the QR standard minimum
DARK_COLOR = "#000"
LIGHT_COLOR = "#fff"


class QrState(IntEnum):
    OK = 0  # png and svg are available
    EMPTY = 1  # no text: nothing to show
    TOO_LONG = 2  # the text does not fit in a QR code
    FAILED = 3  # any other unexpected failure


_TR_CONTEXT = "QrService"


def _message_for(state: QrState) -> str:
    """Friendly, translatable message for a non-OK state."""
    tr = QCoreApplication.translate
    if state == QrState.TOO_LONG:
        return tr(
            _TR_CONTEXT,
            "This text is too long for a QR code. Try shortening it.",
        )
    if state == QrState.FAILED:
        return tr(_TR_CONTEXT, "Could not create a QR code from this text.")
    return ""


@dataclass(frozen=True, repr=False)
class QrResult:
    """Outcome of one generation. Holds image data, never the source text."""

    state: QrState
    png: bytes = field(default=b"")
    svg: str = field(default="")
    dense: bool = False
    message: str = ""

    def __repr__(self) -> str:
        # Never include the text (it is not stored here anyway) or image data.
        return f"QrResult(state={self.state.name}, dense={self.dense})"


def generate_qr(text: str, level: str = DEFAULT_ERROR_LEVEL) -> QrResult:
    """Build PNG and SVG for ``text``. Never raises; see ``QrState``."""
    try:
        if not isinstance(text, str) or text == "":
            return QrResult(QrState.EMPTY)
        level = level.upper() if isinstance(level, str) else ""
        if level not in ERROR_LEVELS:
            return QrResult(QrState.FAILED, message=_message_for(QrState.FAILED))
        dense = len(text) > DENSE_THRESHOLD_CHARS
        try:
            symbol = segno.make(
                text,
                error=level.lower(),
                micro=False,
                boost_error=False,
                encoding="utf-8",
            )
        except segno.DataOverflowError:
            return QrResult(
                QrState.TOO_LONG, dense=dense, message=_message_for(QrState.TOO_LONG)
            )
        png = _save(symbol, "png")
        svg = _save(symbol, "svg").decode("utf-8")
        return QrResult(QrState.OK, png=png, svg=svg, dense=dense)
    except Exception:  # noqa: BLE001 - deliberately drop the details (privacy)
        return QrResult(QrState.FAILED, message=_message_for(QrState.FAILED))


def _save(symbol, kind: str) -> bytes:
    buffer = io.BytesIO()
    symbol.save(
        buffer,
        kind=kind,
        scale=SCALE,
        border=QUIET_ZONE_MODULES,
        dark=DARK_COLOR,
        light=LIGHT_COLOR,
    )
    return buffer.getvalue()


SAVE_KINDS = ("png", "svg")


def save_qr(result: QrResult, path: Path, kind: str = "png") -> bool:
    """Write the PNG or SVG of ``result`` to ``path``. Never raises.

    The format follows the file suffix (.png / .svg, any case). Without one,
    ``kind`` is used and the suffix is appended. Returns True on success. The
    file holds only the QR image, never the source text.
    """
    try:
        if result.state != QrState.OK:
            return False
        path = Path(path)
        suffix = path.suffix.lower().lstrip(".")
        if suffix not in SAVE_KINDS:
            suffix = kind.lower() if isinstance(kind, str) else ""
            if suffix not in SAVE_KINDS:
                return False
            path = path.with_name(path.name + "." + suffix)
        if suffix == "png":
            path.write_bytes(result.png)
        else:
            path.write_bytes(result.svg.encode("utf-8"))
        return True
    except Exception:  # noqa: BLE001 - OSError etc.; details dropped (privacy)
        return False


@QmlElement
@QmlUncreatable("Use the qrService instance provided by the application.")
class QrService(QObject):
    """QML-facing wrapper around ``generate_qr`` holding the latest result."""

    @QEnum
    class State(IntEnum):
        OK = 0
        EMPTY = 1
        TOO_LONG = 2
        FAILED = 3

    resultChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = QrResult(QrState.EMPTY)

    def __repr__(self) -> str:
        return f"QrService(state={self._result.state.name})"

    @Slot(str)
    @Slot(str, str)
    def generate(self, text: str, level: str = DEFAULT_ERROR_LEVEL) -> None:
        """Generate the code for ``text`` (level L/M/Q/H, default M)."""
        self._result = generate_qr(text, level)
        self.resultChanged.emit()

    @Slot()
    def clear(self) -> None:
        """Drop the current result (same as generating an empty text)."""
        self._result = QrResult(QrState.EMPTY)
        self.resultChanged.emit()

    @Slot(QUrl, str, result=bool)
    def saveToFile(self, url: QUrl, kind: str = "png") -> bool:  # noqa: N802
        """Save the current code as PNG or SVG (issue #28).

        ``url`` comes from the file dialog (a file chooser portal path in the
        Flatpak). Returns False on any failure so QML can show a message.
        """
        if not isinstance(url, QUrl) or not url.isLocalFile():
            return False
        return save_qr(self._result, Path(url.toLocalFile()), kind)

    @Property(int, notify=resultChanged)
    def state(self) -> int:
        return int(self._result.state)

    @Property(bool, notify=resultChanged)
    def dense(self) -> bool:
        """True if the text is longer than DENSE_THRESHOLD_CHARS."""
        return self._result.dense

    @Property(str, notify=resultChanged)
    def message(self) -> str:
        """Friendly message for TOO_LONG and FAILED; empty otherwise."""
        return self._result.message

    @Property(QByteArray, notify=resultChanged)
    def png(self) -> QByteArray:
        return QByteArray(self._result.png)

    @Property(str, notify=resultChanged)
    def svg(self) -> str:
        return self._result.svg

    @Property(str, notify=resultChanged)
    def pngDataUrl(self) -> str:  # noqa: N802 - QML-visible name
        """PNG as a data URL for Image.source; empty unless state is OK."""
        if not self._result.png:
            return ""
        encoded = base64.b64encode(self._result.png).decode("ascii")
        return "data:image/png;base64," + encoded

    @Property(int, constant=True)
    def denseThreshold(self) -> int:  # noqa: N802
        return DENSE_THRESHOLD_CHARS
