<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Decision: QR generation library (spike #4)

**Recommendation: use `segno` 1.6.x.** Pure Python, no dependencies, PNG and
SVG built in, BSD-3-Clause license.

Tested on 2026-10-15 with segno 1.6.6, qrcode 8.2, Pillow 12.3, Python 3.14
(the Flatpak will run Python 3.13; both libraries are pure Python and support
it).

## Comparison

| Check | `segno` 1.6.6 | `qrcode` 8.2 |
| --- | --- | --- |
| PNG output | Built in, no dependency (own writer). | Needs Pillow (default) or `pypng` (`qrcode.image.pure`); neither is installed with it. |
| SVG output | Built in, compact (1.2 KB for a short URL). | Built in (`qrcode.image.svg`), but one path element per module (5 KB for the same URL). |
| Error levels L/M/Q/H | Yes (`error='l'/'m'/'q'/'h'`). | Yes (`ERROR_CORRECT_L/M/Q/H`). |
| Quiet zone | `border=` in modules on every writer; default 4 (the QR standard). | `border=` on `QRCode`; default 4. |
| Too-long text | `segno.DataOverflowError`, a subclass of `ValueError`, with a clear message. Catchable. | Plain `ValueError("Invalid version (was 41, expected 1 to 40)")`. Catchable but a vague message, and it cannot be told apart from other `ValueError`s. |
| Runtime dependencies | None. | None (Pillow/pypng optional but needed for PNG). |
| License | BSD-3-Clause, compatible with GPL-3.0-or-later. | BSD-style, compatible with GPL-3.0-or-later. |
| Flatpak packaging | One pure-Python wheel, no dependencies. | One wheel, plus Pillow (native, heavy) or pypng for PNG. |

Both generated identical symbols and identical capacities (see below), so
the choice rests on dependencies, error handling and output quality.

## Pitfalls found (apply these in the Phase 1 service)

`segno.make()` has defaults that are wrong for a clipboard app:

1. **`micro=False` is required.** By default segno may produce a Micro QR
   code, which many phone scanners cannot read.
2. **`boost_error=False` is required.** By default segno silently raises the
   error-correction level if the symbol has spare room (we asked for `M` and
   got `Q` for a short URL). The user's chosen level must be respected.
3. **Pass `encoding='utf-8'`.** Without it, segno may pick ISO-8859-1 for
   text such as "é", which some scanners misread. UTF-8 is the safe choice.
4. **SVG is transparent by default.** Pass `dark='#000'` and `light='#fff'`
   so the SVG carries an explicit white background rectangle. (`qrcode` SVG
   has the same transparency problem.) This is the documented exception to
   "no hardcoded colors": a QR code must be dark modules on a light
   background with a quiet zone, even in dark mode.
5. Keep `border=4` (quiet zone of 4 modules, the QR standard minimum).

Recommended call:

```python
qr = segno.make(text, error="m", micro=False, boost_error=False, encoding="utf-8")
qr.save(buf, kind="png", scale=10, border=4, dark="#000", light="#fff")
qr.save(buf, kind="svg", scale=10, border=4, dark="#000", light="#fff")
```

## Maximum capacity (segno, version 40, no Micro QR)

Measured by bisection with `boost_error=False`. Longer input raises
`segno.DataOverflowError`. Capacity depends on the kind of content, so the
UI should not promise a single character count; "byte" is the worst case and
what URLs and mixed text use.

| Level | Byte mode, ASCII text (chars) | Alphanumeric (`0-9 A-Z space $%*+-./:`) | Numeric only | UTF-8 text, 2 bytes/char (e.g. "é") | UTF-8 text, 3 bytes/char (e.g. "€") |
| --- | --- | --- | --- | --- | --- |
| L | 2953 | 4296 | 7089 | 1476 | 984 |
| M | 2331 | 3391 | 5596 | 1165 | 777 |
| Q | 1663 | 2420 | 3993 | 831 | 554 |
| H | 1273 | 1852 | 3057 | 636 | 424 |

Note: lowercase letters, URLs with lowercase and most real clipboard text use
byte mode, so the first column is the number to show users. A symbol close
to these limits is very dense and hard to scan on a phone; the UI should
consider warning above roughly 1000 characters (issue for Phase 1).

## Verification of samples

Samples are in `docs/spike-qr-library/` (PNG and SVG, level M, scale 10,
quiet zone 4, black on white):

- `sample-url.png` / `.svg`: `https://kde.org/plasma-desktop/` (version 3-M)
- `sample-long-text.png` / `.svg`: 1000 characters of text (version 26-M)

Both PNGs were decoded back to the exact original text with the ZXing-C++
decoder (`zxing-cpp` 3.1.1), as an automated check. **Scanning with a phone
has not been done by me** (no camera). The product owner must scan both PNGs
with a phone and confirm before this spike is closed.

## Flatpak packaging

The manifest (`flatpak/io.github.octaviobernal.KlipperQR.yaml`) gets PySide6
from `io.qt.PySide.BaseApp` and segno from a `python-segno` module: the pinned
wheel `segno-1.6.6-py3-none-any.whl` (URL on files.pythonhosted.org plus
sha256) installed with `pip3 install --no-index --no-deps`. It is one
pure-Python wheel with no dependencies, so it works offline at run time and
needs no Pillow. Tested in a real `flatpak-builder` run and inside the built
sandbox with the network denied (issue #22, see docs/flatpak.md).

### How to update segno

1. Change the version in `requirements.txt` (`segno==X.Y.Z`).
2. On https://pypi.org/project/segno/ (Download files), copy the URL and the
   sha256 of `segno-X.Y.Z-py3-none-any.whl` into the `python-segno` module of
   the manifest. Check the hash yourself: `sha256sum` the downloaded wheel.
   `tests/test_metadata.py` fails if the manifest and `requirements.txt`
   disagree on the version.
3. Rebuild and run the offline check in docs/flatpak.md.

`qrcode` would need Pillow or pypng additionally; I did not check whether
`io.qt.PySide.BaseApp` already ships Pillow, so that path is unverified.

## Out of scope / not done

- No production code, no tests (spike).
- Decoding libraries (Phase 5): `zxing-cpp` was used only in a throwaway
  environment for this check and is not a project dependency.

## Implementation (issue #21)

`src/klipperqr/qr_service.py` applies the pitfalls above. `generate_qr(text,
level="M")` never raises and returns a `QrResult` (`state` OK / EMPTY /
TOO_LONG / FAILED, `png` bytes, `svg` text, `dense`, `message`). `QrService`
wraps it for QML (`qrService.generate(text)`; properties `state`, `dense`,
`message`, `png`, `svg`, `pngDataUrl`). The "dense" threshold is the single
constant `DENSE_THRESHOLD_CHARS` (1000, provisional until a phone scan, #28).
The capacities above were re-checked by the tests with segno 1.6.6. Tests
decode the PNG with Qt and compare it with segno's own matrix; if
`zxing-cpp` and Pillow happen to be installed, one extra test also decodes
the PNG back to the text (not a project dependency).

Guidance for future QML consumers (#24, not tested): show the QR in an
`Image` with `smooth: false`, `fillMode: Image.PreserveAspectFit` and
`cache: false`, so modules stay sharp when scaled and no copy of the
sensitive content stays in Qt's image cache.
