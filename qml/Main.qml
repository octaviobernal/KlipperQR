// SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
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

    // Clipboard state for later issues. Only read-only bindings to the Python
    // service (clipboardService context property); no logic lives here.
    readonly property int clipboardState: clipboardService.state
    readonly property string clipboardText: clipboardService.text
    readonly property bool hasText: clipboardText.length > 0

    // Longest text (in characters) quoted in the QR code's accessible description.
    readonly property int descriptionMaxChars: 80
    readonly property bool showQr: clipboardState === ClipboardService.State.TEXT
        && qrService.state === QrService.State.OK
    // Why there is no QR code: empty text, a clipboard problem, or a generator problem.
    readonly property string problemTitle: {
        if (clipboardState === ClipboardService.State.TEXT) {
            return qrService.state === QrService.State.TOO_LONG
                ? qsTr("Text too long")
                : qsTr("Could not create a QR code");
        }
        return qsTr("No text to encode");
    }
    readonly property string problemExplanation: {
        if (clipboardState === ClipboardService.State.TEXT)
            return qrService.message;
        return clipboardService.message.length > 0
            ? clipboardService.message
            : qsTr("Copy some text, then come back to this window.");
    }

    // Short, plain description of the encoded text for screen readers.
    function describeText(text) {
        const shortened = text.length > descriptionMaxChars
            ? text.substring(0, descriptionMaxChars) + "\u2026"
            : text;
        return qsTr("Encodes: %1").arg(shortened);
    }

    // Regenerate whenever the text changes (clearing it gives an empty QR state).
    // The text is only passed to the Python service; it is never logged here.
    onClipboardTextChanged: qrService.generate(clipboardText)
    Component.onCompleted: qrService.generate(clipboardText)

    pageStack.initialPage: mainPage

    Kirigami.ScrollablePage {
        id: mainPage

        title: qsTr("KlipperQR")

        // Later issues add Kirigami.Action items here (shown in the page
        // toolbar) without restructuring the page.
        actions: []

        // Widest a card should get on a wide window.
        readonly property real maximumContentWidth: Kirigami.Units.gridUnit * 30

        // Later issues add cards as children of this column. Each child sets
        //   Layout.fillWidth: true
        //   Layout.maximumWidth: mainPage.maximumContentWidth
        //   Layout.alignment: Qt.AlignHCenter
        // so content is centered and never stretched too wide. ScrollablePage
        // sizes this column to the page width, so there is no horizontal scroll.
        ColumnLayout {
            id: content

            spacing: Kirigami.Units.largeSpacing

            Kirigami.AbstractCard {
                id: qrCard

                // Square: as wide as the page allows, but not taller than the
                // visible page, and never above the maximum content width.
                readonly property real side: Math.min(
                    mainPage.maximumContentWidth,
                    mainPage.width - 2 * Kirigami.Units.largeSpacing,
                    Math.max(Kirigami.Units.gridUnit * 10,
                             mainPage.height - 2 * Kirigami.Units.largeSpacing))

                Layout.alignment: Qt.AlignHCenter
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
                    Accessible.description: root.describeText(root.clipboardText)
                }
            }

            Kirigami.PlaceholderMessage {
                id: emptyState

                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignHCenter
                Layout.maximumWidth: mainPage.maximumContentWidth
                visible: !root.showQr

                icon.name: root.clipboardState === ClipboardService.State.TEXT
                    ? "dialog-warning" : "view-barcode-qr"
                text: root.problemTitle
                explanation: root.problemExplanation

                Accessible.name: text
                Accessible.description: explanation
                Accessible.role: Accessible.StaticText
            }
        }
    }
}
