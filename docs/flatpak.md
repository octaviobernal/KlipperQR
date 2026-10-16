<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Building and running the Flatpak

Manifest: `flatpak/io.github.octaviobernal.KlipperQR.yaml`

## Runtime and PySide6

- Runtime and SDK: `org.kde.Platform` / `org.kde.Sdk` **6.11** (Qt 6, KDE Frameworks 6, includes Kirigami).
- PySide6 is not in the KDE runtime. It is provided by the Flathub
  `io.qt.PySide.BaseApp` (branch 6.11, matching the runtime). This is the
  lightest route (no pip downloads or wheel lists in our manifest) and is the
  approach Flathub accepts for PySide6 apps. Python is 3.13 in this runtime;
  the manifest installs into `/app/lib/python3.13/site-packages`, so that path
  must be updated when the runtime branch changes.

## Build and run

Needs `flatpak` and `flatpak-builder`.

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.kde.Platform//6.11 org.kde.Sdk//6.11 io.qt.PySide.BaseApp//6.11
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.octaviobernal.KlipperQR.yaml
flatpak run io.github.octaviobernal.KlipperQR
```

If the build fails with a FUSE/rofiles error, add `--disable-rofiles-fuse`.
`build-dir/` and `.flatpak-builder/` are git-ignored.

## Permissions (finish-args)

| Permission | Why |
| --- | --- |
| `--socket=wayland` | Show the window on Wayland (Plasma 6 default). |
| `--socket=fallback-x11` | Show the window on X11 only when Wayland is unavailable. |
| `--share=ipc` | Shared memory with the X server; needed for X11 rendering. |
| `--device=dri` | GPU access for Qt Quick (OpenGL/Vulkan) rendering. |

Not granted: network, filesystem access, D-Bus names. Clipboard/Klipper
permissions are decided in issue #3.
