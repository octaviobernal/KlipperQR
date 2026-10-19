// SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

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

            Kirigami.PlaceholderMessage {
                id: emptyState

                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignHCenter
                Layout.maximumWidth: mainPage.maximumContentWidth
                visible: !root.hasText

                icon.name: "view-barcode-qr"
                text: qsTr("No text to encode")
                explanation: qsTr("Copy some text, then come back to this window.")

                Accessible.name: text
                Accessible.description: explanation
                Accessible.role: Accessible.StaticText
            }
        }
    }
}
