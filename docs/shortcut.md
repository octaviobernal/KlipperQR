<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Open KlipperQR with a keyboard shortcut (Plasma 6, Wayland)

Goal: copy some text, press a key combination, KlipperQR opens and shows the
QR code.

## Why the app has no global shortcut of its own

On Wayland an app cannot grab keys while another window has focus. Only the
desktop (Plasma) can do that. So you bind the shortcut in Plasma, and Plasma
starts KlipperQR. The app then reads the clipboard only once its window is
active (see [clipboard.md](clipboard.md)); it never watches the clipboard in
the background.

## Launch commands

| Install | Command |
|---|---|
| Flatpak | `flatpak run io.github.octaviobernal.KlipperQR` |
| From a checkout | `python3 /full/path/to/KlipperQR/src/klipperqr/main.py` |

For a checkout, use the absolute path of your own clone. If you use a virtual
environment, call its interpreter instead, for example
`/full/path/to/KlipperQR/.venv/bin/python3`.

## Route A: give the menu entry a shortcut (Flatpak, recommended)

The Flatpak installs a desktop file, so KlipperQR appears in the application
launcher (category Utilities). You can pin it there and give it a shortcut
without typing a command.

1. Open **System Settings > Keyboard > Shortcuts**.
2. Click **Add New > Application...** and choose **KlipperQR** in the list.
3. Select the new KlipperQR entry, click **None** next to "Launch" (or **Add
   custom shortcut**), then press your key combination, for example
   Meta+Q.
4. Click **Apply**.

To pin it instead: right-click KlipperQR in the application launcher and pick
**Pin to Task Manager** (or **Add to Favorites**).

## Route B: custom command (Flatpak or checkout)

1. Open **System Settings > Keyboard > Shortcuts**.
2. Click **Add New > Command or Script...**.
3. Enter the launch command from the table above and confirm.
4. Set your key combination on the new entry and click **Apply**.

## Use it

1. Copy the text or link in any app.
2. Press your shortcut. KlipperQR opens and reads the clipboard as soon as its
   window is active.
3. If the window was already open, the shortcut may not raise it. Click the
   window, or press **Paste** (Ctrl+Shift+V).

## Verification status

Menu names are written for Plasma 6 and can differ slightly between versions.

| Step | Status |
|---|---|
| Route A (Add New > Application) on a Plasma Wayland session | Not verified yet, needs a person to run it |
| Route B (Add New > Command) with the Flatpak command | Not verified yet |
| Route B with the checkout command | Not verified yet |
| Raising an already open window from the shortcut | Not verified yet |

A person must follow these steps on a real Plasma Wayland session and record
the result in issue #39, then update this table.
