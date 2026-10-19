// SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import KlipperQR

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("KlipperQR")
    width: Kirigami.Units.gridUnit * 30
    height: Kirigami.Units.gridUnit * 28
    // About 360 px at the default scale: the width of a Plasma Mobile screen.
    minimumWidth: Kirigami.Units.gridUnit * 20
    minimumHeight: Kirigami.Units.gridUnit * 16

    // Read-only binding to the Python clipboard service (clipboardService
    // context property); no clipboard logic lives here.
    readonly property int clipboardState: clipboardService.state

    // The text the QR code encodes. It follows the text field (after a short
    // typing delay) and is replaced by clipboard reads according to the rules
    // in ClipboardService (see syncFromClipboard). Held in memory only.
    property string encodedText: ""
    readonly property bool hasText: encodedText.length > 0

    // Longest text (in characters) quoted in the QR code's accessible description.
    readonly property int descriptionMaxChars: 80
    // Delay after the last keystroke before the QR code is rebuilt.
    readonly property int typingDelayMs: 250
    readonly property bool showQr: hasText && qrService.state === QrService.State.OK
    // Why there is no QR code: empty text or a generator problem.
    readonly property string problemTitle: {
        if (!hasText)
            return qsTr("No text to encode");
        return qrService.state === QrService.State.TOO_LONG
            ? qsTr("Text too long")
            : qsTr("Could not create a QR code");
    }
    readonly property string problemExplanation: {
        if (hasText)
            return qrService.message;
        // Friendly clipboard message (empty / not text), if any, then the
        // always-shown hint about the clipboard limits.
        return clipboardService.message.length > 0
            ? clipboardService.message + "\n\n" + clipboardHint
            : clipboardHint;
    }
    readonly property string clipboardHint: qsTr("Copy some text in another app, then come back here or press Paste. KlipperQR can only read the clipboard while this window is active.")
    readonly property string pasteShortcutText: qsTr("Ctrl+Shift+V")

    // Short, plain description of the encoded text for screen readers.
    function describeText(text) {
        const shortened = text.length > descriptionMaxChars
            ? text.substring(0, descriptionMaxChars) + "\u2026"
            : text;
        return qsTr("Encodes: %1").arg(shortened);
    }

    // Use `text` now (no typing delay) and rebuild the QR code.
    // The text is only passed to the Python service; it is never logged here.
    function applyText(text) {
        typingTimer.stop();
        encodedText = text;
        qrService.generate(text);
    }

    Component.onCompleted: applyText(encodedText)

    Timer {
        id: typingTimer

        interval: root.typingDelayMs
        onTriggered: root.applyText(textField.text)
    }

    // ClipboardService decides what a read means (issue #41): an explicit
    // read (Paste) or NEW clipboard text replaces the field, and clear()
    // empties it. Unchanged, empty or not-text clipboards on refocus
    // (UNCHANGED/IGNORED) leave the user's edits alone.
    Connections {
        target: clipboardService

        function onReadFinished(outcome) {
            if (outcome === ClipboardService.Outcome.EXPLICIT
                    || outcome === ClipboardService.Outcome.NEW_TEXT
                    || outcome === ClipboardService.Outcome.NONE) {
                textField.text = clipboardService.text;
                root.applyText(clipboardService.text);
            }
        }
    }

    pageStack.initialPage: mainPage

    Kirigami.ScrollablePage {
        id: mainPage

        title: qsTr("KlipperQR")

        // Later issues add more Kirigami.Action items here.
        actions: [
            Kirigami.Action {
                id: pasteAction
                objectName: "pasteAction"

                icon.name: "edit-paste"
                text: qsTr("Paste")
                // Ctrl+Shift+V: plain Ctrl+V already pastes inside the text field.
                shortcut: "Ctrl+Shift+V"
                tooltip: qsTr("Paste text from the clipboard (%1)").arg(root.pasteShortcutText)
                // Explicit read: always shows the result (see ClipboardService.read).
                // Accessible name: a toolbar button is named after `text`
                // ("Paste"); the tooltip carries the shortcut.
                onTriggered: clipboardService.read()
            }
        ]

        // Widest a card should get on a wide window.
        readonly property real maximumContentWidth: Kirigami.Units.gridUnit * 30
        // Wide window: the QR card and the text card sit side by side.
        readonly property bool wide: width >= Kirigami.Units.gridUnit * 40
        // Width available to one card.
        readonly property real cardWidth: Math.min(
            maximumContentWidth,
            wide ? (width - 3 * Kirigami.Units.largeSpacing) / 2
                 : width - 2 * Kirigami.Units.largeSpacing)

        // ScrollablePage sizes this column to the page width, so there is no
        // horizontal scroll. Cards are centered and never stretched too wide.
        ColumnLayout {
            id: content

            spacing: Kirigami.Units.largeSpacing

            GridLayout {
                Layout.alignment: Qt.AlignHCenter
                columns: mainPage.wide ? 2 : 1
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.largeSpacing

                Kirigami.AbstractCard {
                    id: qrCard

                    // Square: as wide as allowed, but not taller than the
                    // visible page.
                    readonly property real side: Math.min(
                        mainPage.cardWidth,
                        Math.max(Kirigami.Units.gridUnit * 10,
                                 mainPage.height - 2 * Kirigami.Units.largeSpacing))

                    Layout.alignment: Qt.AlignHCenter | Qt.AlignTop
                    Layout.preferredWidth: side
                    Layout.preferredHeight: side
                    visible: root.showQr

                    contentItem: Image {
                        // Fresh data URL for every code; not cached, so old
                        // images are released and nothing is written to disk.
                        source: qrService.pngDataUrl
                        cache: false
                        asynchronous: false
                        fillMode: Image.PreserveAspectFit
                        // Nearest-neighbour scaling keeps module edges crisp. The
                        // PNG is 10 px per module, so it is sharp up to 200% scaling.
                        smooth: false
                        mipmap: false

                        Accessible.role: Accessible.Graphic
                        Accessible.name: qsTr("QR code")
                        Accessible.description: root.describeText(root.encodedText)
                    }
                }

                Kirigami.AbstractCard {
                    id: textCard

                    Layout.alignment: Qt.AlignHCenter | Qt.AlignTop
                    Layout.preferredWidth: root.showQr ? qrCard.side : mainPage.cardWidth

                    contentItem: ColumnLayout {
                        spacing: Kirigami.Units.smallSpacing

                        Kirigami.Heading {
                            Layout.fillWidth: true
                            level: 4
                            text: qsTr("Text in the QR code")
                            Accessible.role: Accessible.StaticText
                            Accessible.name: text
                        }

                        // Limited height: long text scrolls inside the field.
                        Controls.ScrollView {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Kirigami.Units.gridUnit * 8

                            Controls.TextArea {
                                id: textField
                                objectName: "encodedTextField"

                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                placeholderText: qsTr("Type or paste the text to put in the QR code")
                                // Rebuild the QR code shortly after the last keystroke.
                                onTextChanged: typingTimer.restart()

                                Accessible.role: Accessible.EditableText
                                Accessible.name: qsTr("Text in the QR code")
                                Accessible.description: qsTr("The QR code is built from this text. You can edit it.")
                            }
                        }
                    }
                }
            }

            Kirigami.PlaceholderMessage {
                id: emptyState

                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                Layout.maximumWidth: mainPage.maximumContentWidth
                visible: !root.showQr

                icon.name: root.hasText ? "dialog-warning" : "view-barcode-qr"
                text: root.problemTitle
                explanation: root.problemExplanation

                Accessible.name: text
                Accessible.description: explanation
                Accessible.role: Accessible.StaticText
            }
        }
    }
}
