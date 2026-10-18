// SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as QQC2

// Throwaway spike file (#5). Not production code.
QQC2.ApplicationWindow {
    visible: true
    width: 360
    height: 160
    title: qsTr("Translation spike")

    Column {
        anchors.centerIn: parent
        spacing: 8
        QQC2.Label {
            objectName: "greeting"
            text: qsTr("Paste from clipboard")
        }
        QQC2.Label {
            objectName: "plural"
            //: Shown under the QR code; %n is the number of characters
            text: qsTr("%n character(s)", "", pocBackend.count)
        }
        QQC2.Label {
            objectName: "fromPython"
            text: pocBackend.message
        }
    }
}
