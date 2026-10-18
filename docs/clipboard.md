<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Spike (#3): how KlipperQR reads the clipboard

Status: decision proposed. Focused Qt read confirmed on the host; Flatpak run still to confirm (see "Not verified").

## How it was tested

Throwaway script `docs/spike-clipboard/poc_clipboard.py` (not production code).
It prints only metadata (focused yes/no, success, text length), never the
clipboard text. Only the harmless text `dummy-test-text` was copied during tests.

Environment: KDE Plasma (Wayland, `XDG_SESSION_TYPE=wayland`), Klipper running
inside plasmashell (`org.kde.klipper` on the session bus), PySide6 6.10.2 on
the host, Flatpak build of this repo (`org.kde.Platform` 6.11 + PySide6 BaseApp).
The sandbox permissions used are those in `flatpak/*.yaml` (no D-Bus access).

## Results

| Option | Works? | When | Flatpak permission | Privacy |
| --- | --- | --- | --- | --- |
| (a) Qt `QClipboard` read | Window NOT focused: **no**. `hasText` was false, text empty, on host and in Flatpak. Focused: **not verified by me** (see below); expected yes, this is Wayland's rule. | Only while our window has keyboard focus | None (Wayland socket already granted) | Best: the app sees the clipboard only while the user is looking at it |
| (b) Explicit Paste / Refresh button (same Qt read, triggered by the user) | Same API as (a). A click or key press means the window is focused, so it is the reliable form of (a). Focused behaviour not verified by me. | On user action | None | Best: reads only when the user asks |
| (c) Klipper over D-Bus (`getClipboardContents`) | **Yes, even unfocused**, on the host. In the Flatpak it **fails** (`ServiceUnknown`) with our current permissions and **works** after adding `--talk-name=org.kde.klipper`. | Any time | `--talk-name=org.kde.klipper` | Worst: any time, without the user acting, and the same permission lets the app read the clipboard of every other app; it can also `setClipboardContents` and `clearClipboardHistory`. Only works if Klipper runs (Plasma only). Flathub reviewers usually question talk-name permissions. |

## Recommendation

Use **(b) with (a)** as the only mechanism: read the clipboard with Qt, when
the app window is focused and when the user presses "Paste from clipboard"
(and once when the window gains focus, if cheap). Do not use Klipper.

Why, in plain words: on Wayland an app is not allowed to peek at the clipboard
while you are working in another window; that rule exists to protect
passwords. The Qt way respects that rule, needs no extra Flatpak permission,
works on every desktop and on X11, and is easier to get through Flathub
review. Klipper would work in the background, but it needs a special hole in
the sandbox and gives KlipperQR more access than a QR generator should have.
Cost: the QR is not updated by itself while you copy things in another app;
you come back to the window or press Paste.

Implementation notes for Phase 1: read on the UI thread (it is fast, local
data); never log or store the text; handle empty / non-text clipboard
(`mimeData().hasText()`); `QClipboard.dataChanged` is only useful while focused.

## Not verified

- Verified on the host (Plasma Wayland): once the test window is really mapped
  (`QRasterWindow`; a bare `QWindow` is never shown on Wayland), it gets focus and
  the Qt read returns `focused=True`, `hasText=True`, with the correct length.
- Still open: the same focused read inside the Flatpak. Please verify (30 seconds):
  1. `wl-copy "dummy-test-text"`
  2. `python3 docs/spike-clipboard/poc_clipboard.py 20`
  3. Click the small window; the output must change to `focused=True` and `qt(hasText,len)=(True, 15)`.
  4. For the Flatpak, run the same script with
     `flatpak run --command=python3 --filesystem=$PWD/docs/spike-clipboard:ro io.github.octaviobernal.KlipperQR $PWD/docs/spike-clipboard/poc_clipboard.py 20`.
  If this fails, the recommendation must be revisited (fallback: `Ctrl+V` into a text field).
- X11 session, and non-Plasma Wayland compositors: not tested.

## Limits text (draft)

README:

> **Clipboard limits.** On Wayland, apps may only read the clipboard while their
> window is in focus. KlipperQR therefore reads the clipboard when you open or
> focus the window or press "Paste from clipboard". It cannot watch the
> clipboard in the background. KlipperQR never stores or sends clipboard text.

In-app hint (short, wrap in `qsTr()`):

> Copy some text in another app, then come back here or press Paste. KlipperQR can only read the clipboard while this window is active.

## Proposed follow-up issues (for the BA)

1. Clipboard service (Python QObject): read text via `QClipboard` on demand and on window focus; empty/non-text handling; no logging/persistence; unit tests with a fake clipboard.
2. Paste / Refresh action in the UI (Kirigami.Action, shortcut Ctrl+Shift+V or similar, accessible name) plus the in-app limits hint.
3. Add the limits text to the README.
4. Manual test checklist for focus behaviour on Wayland and X11 (Flatpak).
5. Optional, later, only if users ask: Klipper integration behind an opt-in, documenting the `--talk-name=org.kde.klipper` permission and Flathub review risk.
