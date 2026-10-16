// SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("KlipperQR")
    width: Kirigami.Units.gridUnit * 30
    height: Kirigami.Units.gridUnit * 24

    pageStack.initialPage: Kirigami.Page {
        title: qsTr("KlipperQR")

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            icon.name: "view-barcode-qr"
            text: qsTr("QR codes will appear here")
            explanation: qsTr("This is a placeholder page.")

            Accessible.name: text
            Accessible.role: Accessible.StaticText
        }
    }
}
