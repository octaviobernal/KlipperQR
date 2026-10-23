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

## Python libraries (segno)

segno (QR generation) is the only extra library. The `python-segno` module in
the manifest installs a pinned wheel (URL + sha256) with
`pip3 install --no-index --no-deps`; Flathub forbids unpinned downloads at
build time. No Pillow. How to update it: [docs/qr-library.md](qr-library.md).

## Check QR generation offline in the built Flatpak

After `flatpak-builder ... build-dir ...` (no `--install` needed), run the
headless script inside the sandbox with the network denied. It prints only
metadata (never clipboard text) and exits 0 on success:

```sh
flatpak build --unshare=network --filesystem="$PWD/scripts:ro" \
  --env=QT_QPA_PLATFORM=offscreen build-dir python3 "$PWD/scripts/flatpak-smoke.py"
```

CI runs this same command after the Flatpak build (the `flatpak` job in
`.github/workflows/ci.yml`), so a missing runtime dependency such as segno
turns the job red. The script treats only "network unreachable" style errors
(ENETUNREACH, EACCES, EPERM, `socket.gaierror`) as "network denied"; any other
error, including a timeout, makes it exit non-zero.

## Translations

The manifest runs `flatpak/install-translations.sh`, which compiles each
`translations/klipperqr_*.ts` to `.qm` with `lrelease` (Qt 6, part of
`org.kde.Sdk`) and installs them in `/app/share/klipperqr/translations`, the
folder `main.py` searches. It exits with an error (so the build fails) if no
catalog or no non-empty `.qm` is produced. No extra permission is needed.

Check Spanish in the built Flatpak (headless). Set both `LC_ALL` and `LANG`:
the sandbox sets `LC_ALL=en_US.utf8`, which would otherwise win.

```sh
flatpak build --filesystem="$PWD/scripts:ro" --env=QT_QPA_PLATFORM=offscreen \
  --env=LC_ALL=es_ES.UTF-8 --env=LANG=es_ES.UTF-8 \
  build-dir python3 "$PWD/scripts/flatpak-i18n-smoke.py"
```

To look at the real window in Spanish after `--install`:
`flatpak run --env=LC_ALL=es_ES.UTF-8 --env=LANG=es_ES.UTF-8 io.github.octaviobernal.KlipperQR`.

## Permissions (finish-args)

| Permission | Why |
| --- | --- |
| `--socket=wayland` | Show the window on Wayland (Plasma 6 default). |
| `--socket=fallback-x11` | Show the window on X11 only when Wayland is unavailable. |
| `--share=ipc` | Shared memory with the X server; needed for X11 rendering. |
| `--device=dri` | GPU access for Qt Quick (OpenGL/Vulkan) rendering. |

Not granted: network, filesystem access, D-Bus names (a test fails if any
is added; see [privacy.md](privacy.md)). Clipboard/Klipper
permissions are decided in issue #3.

## App ID and metadata files

The app ID is `io.github.octaviobernal.KlipperQR`. In code it is defined once
as `APP_ID` in `src/klipperqr/main.py`. File names cannot import it, so
`tests/test_metadata.py` checks that the manifest, desktop file, AppStream
file and icon all use that same ID.

| File | Installed to (in the Flatpak) |
| --- | --- |
| `data/io.github.octaviobernal.KlipperQR.desktop` | `/app/share/applications/` |
| `data/io.github.octaviobernal.KlipperQR.metainfo.xml` | `/app/share/metainfo/` |
| `data/io.github.octaviobernal.KlipperQR.svg` (app icon, GPL-3.0-or-later) | `/app/share/icons/hicolor/scalable/apps/` |

Check them with:

```sh
desktop-file-validate data/io.github.octaviobernal.KlipperQR.desktop
appstreamcli validate --no-net data/io.github.octaviobernal.KlipperQR.metainfo.xml
```

Screenshots live in `docs/screenshots/` and are referenced by their
`raw.githubusercontent.com` URL pinned to the `v1.0.0` tag. They are real captures of the app
window (Breeze, no clipboard data). Until the tag is pushed, the network
check (`appstreamcli validate` without `--no-net`) reports
`screenshot-image-not-found`; CI stays offline. For the
Flathub submission steps see [flathub.md](flathub.md).
