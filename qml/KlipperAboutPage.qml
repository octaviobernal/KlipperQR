// SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import org.kde.kirigami as Kirigami

// Kirigami's AboutPage fed with a plain object (KAboutData has no official
// PySide6 bindings). Facts come from the Python `appInfo` object.
Kirigami.AboutPage {
    objectName: "aboutPage"

    aboutData: ({
        "displayName": qsTr("KlipperQR"),
        "productName": "klipperqr",
        "componentName": appInfo.appId,
        "desktopFileName": appInfo.appId,
        "shortDescription": qsTr("Turn copied text or links into a QR code"),
        "homepage": appInfo.homepage,
        "bugAddress": appInfo.bugTracker,
        "version": appInfo.version,
        "otherText": qsTr("KlipperQR works entirely on your device. Nothing you copy or type is sent anywhere."),
        "copyrightStatement": qsTr("© 2026 Octavio Bernal"),
        "authors": [
            {
                "name": "Octavio Bernal",
                "task": qsTr("Author"),
                "emailAddress": "",
                "webAddress": "",
                "ocsUsername": ""
            }
        ],
        "credits": [],
        "translators": [],
        "components": [
            {
                "name": qsTr("segno (QR code library, BSD-3-Clause license)"),
                "version": appInfo.segnoVersion,
                "description": "",
                "webAddress": "https://github.com/heuer/segno",
                "licenses": []
            }
        ],
        "licenses": [
            {
                "name": qsTr("GNU General Public License, version 3 or later"),
                "spdx": "GPL-3.0-or-later",
                "text": qsTr("KlipperQR is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. See https://www.gnu.org/licenses/gpl-3.0.html for the full text.")
            }
        ]
    })
}
