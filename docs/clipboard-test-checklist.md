<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Manual clipboard test checklist

Run this before each release. Clipboard focus rules differ between Wayland,
X11 and Flatpak, so they cannot be fully automated. Background and decision:
[clipboard.md](clipboard.md).

## Safety rules

- Use **only harmless dummy text**: `dummy-test-text`. Never copy a password,
  token or any real data while testing.
- Do not log or paste clipboard content into notes, issues or terminals. Write
  down only pass/fail. If a step needs a terminal, use commands that print
  nothing from the clipboard.
- Clearing the clipboard afterwards is fine (copy `dummy-test-text` again, or
  clear it in Klipper).

## Setup

Run once for each environment in the results table.

- Host: `python3 src/klipperqr/main.py` (see [CONTRIBUTING](../CONTRIBUTING.md)).
- Flatpak: `flatpak run io.github.octaviobernal.KlipperQR`
  (build steps: [flatpak.md](flatpak.md)).
- To put dummy text on the clipboard: type it in any text editor, select it and
  press Ctrl+C. On Wayland, `wl-copy "dummy-test-text"` also works.
- To put non-text on the clipboard: copy an image (for example, in Spectacle
  take a screenshot and choose copy to clipboard, or use KlipperQR's own
  "Copy image").

## Steps

Mark each step Pass, Fail or Skip (with a reason) per environment.

### 1. Focused read

1. Copy `dummy-test-text` in another app.
2. Click or Alt+Tab to the KlipperQR window.
3. Expected: the text field shows `dummy-test-text` and a QR code appears, with
   no button press.
4. Close KlipperQR, copy the dummy text again, start KlipperQR. Expected: the
   same on first open.

### 2. Unfocused read (friendly message, no text)

1. With KlipperQR open and not the active window (another window has focus),
   copy a new dummy text, for example `dummy-test-text-2`, in the other app.
2. Look at KlipperQR without clicking it (for example, a second monitor or a
   side-by-side layout, but do not activate it).
3. Expected: KlipperQR does **not** show the new text (on Wayland it is not
   allowed to read it). Nothing crashes and no error dialog opens.
4. Now activate the KlipperQR window. Expected: the new text appears.
5. Check the hint text is visible on the empty state: "Copy some text in
   another app, then come back here or press Paste. KlipperQR can only read the
   clipboard while this window is active."

### 3. Paste action

1. Copy `dummy-test-text-3` in another app, then focus KlipperQR.
2. Press **Clear** (Ctrl+Shift+Delete). Expected: text and QR code disappear.
3. Press **Paste** (Ctrl+Shift+V) and also try the toolbar button with the
   mouse. Expected: `dummy-test-text-3` and its QR code return each time.
4. Edit the text field by hand, then press Paste. Expected: the pasted text
   replaces what you typed.

### 4. Empty clipboard

1. Empty the clipboard (for example, clear Klipper history, or restart the
   session on a fresh login before copying anything).
2. Focus KlipperQR and press **Paste**.
3. Expected: a friendly message ("The clipboard is empty or cannot be read
   right now."), the text field and QR code that were shown before stay unchanged
   (if the field was empty, nothing appears), no crash.

### 5. Non-text clipboard

1. Copy an image (see Setup).
2. Focus KlipperQR and press **Paste**.
3. Expected: the message "The clipboard does not contain text." is shown, the
   previously shown text and QR code are kept (not cleared), no crash.
4. Focus away and back (automatic read). Expected: the previously shown text
   and QR code are still there and no error is shown.

### 6. Privacy spot check

1. Run the app from a terminal while doing steps 1 to 5.
2. Expected: the terminal shows no clipboard text (not even `dummy-test-text`).

## Results

Record the date, KlipperQR version or commit, and the person. "Not yet
verified" means nobody has run these steps in that environment.

| Environment | Steps 1 to 6 | Date / version / tester |
| --- | --- | --- |
| Plasma Wayland, host | Pass (all steps) | 2026-10-20, commit c94e308, Octavio Bernal |
| Plasma Wayland, Flatpak | Not yet run against this checklist (see note) | |
| Plasma X11, host | Not yet verified | |
| Plasma X11, Flatpak | Not yet verified | |
| Non-Plasma Wayland (for example GNOME, Sway), host | Not yet verified | |
| Non-Plasma Wayland, Flatpak | Not yet verified | |

Note: the spike (#3) confirmed on Plasma Wayland, host and Flatpak, that a
focused Qt read works and an unfocused read returns no text (see the
verification log in [clipboard.md](clipboard.md)). It used a throwaway script,
not the app UI, so it does not count as a run of this checklist. The first
full run of this checklist was done on Plasma Wayland, host (see the table).
The Flatpak run still needs a person at a Plasma Wayland session; record it in
the table above.
