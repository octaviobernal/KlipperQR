<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Privacy

KlipperQR treats clipboard text as sensitive. The promise, in plain words:

- Nothing leaves your device. The app makes no network requests.
- Nothing is logged. The app prints nothing that contains your text.
- Nothing is stored. The text lives in memory only; no settings, no cache, no
  temporary files.
- There is no history. Only the current text is shown.

The only file KlipperQR ever writes is the PNG or SVG you choose to save with
"Save". It contains the QR image only (never the text as readable text, never
in the file name), although anyone can of course scan the image.

## How this is checked

All checks run in `pytest` (file `tests/test_privacy.py`) and in CI.

| Check | How |
| --- | --- |
| Flatpak asks for no network, `--filesystem`, `--talk-name` (or other bus names) | `test_manifest_requests_no_network_filesystem_or_bus_names` |
| No logging, printing, `QSettings`, temp files, network code, or file reads/writes in `src/` and `qml/` | `test_no_logging_printing_settings_or_temp_files_in_app_code` |
| The only file writes are the PNG/SVG export | `test_only_save_qr_writes_files` |
| Running the real window (copy, read, generate, save, clear, close) prints nothing with the text and leaves no file with it in the data, config, cache, state or runtime folders | `scripts/privacy-check.py`, run by `test_runtime_run_leaves_no_trace` |

To run the runtime check by hand: `python3 scripts/privacy-check.py`. It uses
a made-up marker text, private temporary XDG folders, the offscreen platform
and the most verbose Qt logging. To check a real session, start the app from a
terminal (`python3 src/klipperqr/main.py`, or `flatpak run
io.github.octaviobernal.KlipperQR`), copy, generate, save and clear, and look
for your text in the output.

## Code review result (issue #31)

Reviewed `src/klipperqr/*.py`, `qml/*.qml` and `flatpak/`.

| Area | Finding |
| --- | --- |
| Logging / printing | None: no `print`, `logging`, `qDebug`, `console.*`. `clipboard_service.py` and `qr_service.py` state this in their docstrings. |
| Exceptions | Caught with `except Exception` and details dropped; no message includes text. |
| `repr()` | `ClipboardService` and `QrService` show state names only, never text. |
| Settings | No `QSettings` or any other settings use. |
| Files / temp files | The only writes are `write_bytes` in `save_qr` (QR image, to the path the user chose in the file dialog). No temp files. |
| Comparing clipboard changes | Done with SHA-256 digests held in memory, not the text. |
| Network | None in code; the Flatpak has no network permission. |
| Clear | `clearAll()` empties the field, the QR result and the clipboard service text. The system clipboard itself is not touched (documented in `qml/Main.qml`). |

Known limits, not caused by the app: the text stays in the system clipboard
(and in a clipboard manager such as Klipper, if you run one) until you copy
something else, and a QR image copied with "Copy image" or saved to disk can be
scanned by anyone who sees it.

## Open item

The acceptance criterion "run with the app in a terminal" was verified here
with the automated offscreen run, not by hand in a live Plasma session with a
real Wayland clipboard. Repeat that once before release.
