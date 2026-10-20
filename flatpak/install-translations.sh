#!/bin/sh
# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Compile translations/*.ts to .qm and install them where the app looks
# (<prefix>/share/klipperqr/translations). Run from the repository root by the
# Flatpak manifest, with `lrelease` (Qt 6, from org.kde.Sdk) on PATH.
# Fails the build if no .qm file was produced, so the Flatpak can never ship
# without translations by accident.
set -eu

dest="${1:-/app/share/klipperqr/translations}"

count=0
for ts in translations/klipperqr_*.ts; do
    [ -e "$ts" ] || continue
    qm="${ts%.ts}.qm"
    lrelease "$ts" -qm "$qm"
    [ -s "$qm" ] || { echo "ERROR: lrelease produced no $qm" >&2; exit 1; }
    install -Dm644 "$qm" -t "$dest"
    count=$((count + 1))
done

if [ "$count" -eq 0 ]; then
    echo "ERROR: no translations/klipperqr_*.ts found; refusing to build a Flatpak without translations" >&2
    exit 1
fi
echo "Installed $count compiled translation catalog(s) to $dest"
