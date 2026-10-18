# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""THROWAWAY proof of concept for issue #3. NOT production code.

Probes three ways to read clipboard text and prints ONLY metadata
(window focused or not, success, text length). It never prints, logs or
stores the clipboard content itself.

Run: python3 poc_clipboard.py [seconds]
"""

import sys

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtDBus import QDBusConnection, QDBusInterface
from PySide6.QtGui import QColor, QGuiApplication, QRasterWindow


def qt_read(app):
    cb = app.clipboard()
    mime = cb.mimeData()
    has_text = bool(mime and mime.hasText())
    return has_text, len(cb.text()) if has_text else 0


def klipper_read():
    iface = QDBusInterface(
        "org.kde.klipper",
        "/klipper",
        "org.kde.klipper.klipper",
        QDBusConnection.sessionBus(),
    )
    if not iface.isValid():
        return "unavailable: " + iface.lastError().name()
    reply = iface.call("getClipboardContents")
    args = reply.arguments()
    if reply.type().name != "ReplyMessage" and not args:
        return "error: " + reply.errorName()
    return f"ok len={len(args[0])}"


def _paint(win):
    from PySide6.QtGui import QPainter

    p = QPainter(win)
    p.fillRect(QRect(0, 0, win.width(), win.height()), QColor("lightgray"))
    p.drawText(20, 55, "click me")
    p.end()


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    app = QGuiApplication(sys.argv)
    # QRasterWindow paints a buffer; a bare QWindow is never mapped on Wayland.
    win = QRasterWindow()
    win.setTitle("clipboard poc")
    win.resize(300, 100)
    win.paintEvent = lambda ev: _paint(win)
    win.show()
    win.requestActivate()
    n = [0]

    def probe():
        n[0] += 1
        focused = app.applicationState() == Qt.ApplicationState.ApplicationActive
        print(
            f"t={n[0]}s focused={focused} (a) qt(hasText,len)={qt_read(app)} "
            f"(c) klipper={klipper_read()}",
            flush=True,
        )

    t = QTimer()
    t.timeout.connect(probe)
    t.start(1000)
    QTimer.singleShot(seconds * 1000, app.quit)
    app.exec()


if __name__ == "__main__":
    main()
