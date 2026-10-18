<!--
SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Spike (#5): translations and settings for KlipperQR

Status: decision made. Qt translations plus QSettings were tested on the host
and in the Flatpak. Items marked "expected, not tested" were not run.

KI18n (translations) and KConfig (settings) are C++ KDE Frameworks with no
official PySide6 bindings, so we use the Qt equivalents instead.

## How it was tested

Throwaway files in `docs/spike-i18n/` (not production code): `Poc.qml`,
`poc_i18n.py`, and `klipperqr_es.ts` (a Spanish catalog, 4 strings).
Environment: KDE Plasma on Wayland, PySide6 6.10.2 on the host, and the
existing Flatpak build (KDE runtime 6.11 with the PySide6 BaseApp). The window
was run with `QT_QPA_PLATFORM=offscreen` and the text of the labels was read
back from QML. A real on-screen look at the window has not been done (see
"Needs a human").

## Translation options

| | A. Qt tooling (`qsTr`, `self.tr`, `.ts`/`.qm`) | B. gettext (`.po`/`.mo`) | C. Custom JSON/dict |
| --- | --- | --- | --- |
| In QML | `qsTr("text")`, built in | No built-in support. Needs our own `i18n()` helper exposed from Python | Same, own helper |
| In Python | `self.tr("text")` in a `QObject`, or `QCoreApplication.translate("Context", "text")` | `gettext.gettext` / `_()` | own code |
| Extraction | `pyside6-lupdate` reads both `.qml` and `.py` (tested, see below) | `xgettext` for Python; QML only via `--language=JavaScript` plus a helper name (expected, not tested). `xgettext` is not installed on this machine | own tool |
| Plurals | `qsTr("%n item(s)", "", n)`; tested, gave "3 caracteres" | `ngettext` | own code |
| Context / translator notes | `qsTr("text", "disambiguation")`, `//:` comments become `<extracomment>` (tested) | `pgettext`, `#.` comments | none |
| Runtime loading | `QTranslator` loads a `.qm` (tested) | `gettext.translation(...)` | own code |
| Extra dependencies | None: `pyside6-lupdate` and `pyside6-lrelease` ship with PySide6 (found in `/usr/bin` here) | `gettext` tools on the contributor machine | none |
| KDE translators | KDE's own l10n system (Scripty, Lokalize, the "l10n-kf6" PO workflow) is gettext-based. Lokalize reading `.ts` is expected not to work well (not tested). Weblate and Transifex do support Qt `.ts` (from their docs, not tested here) | Fits KDE's PO workflow best | Poor |
| Flathub | Nothing special: install the `.qm` files into `/app/share/klipperqr/translations` | Install the `.mo` files; same idea | Same |

## Settings options

| | `QSettings` | Own config file (JSON/INI in `QStandardPaths`) | KConfig |
| --- | --- | --- | --- |
| Available from PySide6 | Yes, part of Qt | Yes, but we write and test parsing ourselves | No official PySide6 bindings (not usable) |
| Location on host | `~/.config/<Org>/<App>.conf` (tested) | whatever we choose | `~/.config/<app>rc` |
| Location in Flatpak | Tested: `~/.var/app/io.github.octaviobernal.KlipperQR/config/<Org>/<App>.conf`. It is inside the sandbox's own `XDG_CONFIG_HOME`, so it needs no extra permission, and it survives app updates | Same folder if we use `QStandardPaths.AppConfigLocation` (expected, not tested) | n/a |
| Reads KDE's `kdeglobals`? | No. The app does not need it for its own preferences | No | Yes |
| Typed values, change notification | Basic (strings, ints, bools; we convert types ourselves, since INI returns strings in some cases) | Whatever we write | n/a |
| Code to maintain | Almost none | More | n/a |

## Recommendation

**Translations: option A (Qt tooling), with the default Qt catalog name
`klipperqr_<lang>.ts`.**

- Mark every user-visible string with `qsTr()` in QML and `self.tr()` (or
  `QCoreApplication.translate`) in Python, from the first issue on. Use
  `//:` comments in QML to give translators context (tested in QML; the
  Python equivalent was not tested).
- Source language is English. Do not translate in the QML; the source string
  is the fallback, so a missing translation shows English.
- One `QTranslator` is installed in `main.py` before the QML is loaded, using
  the system locale (`QLocale()`); the `.qm` directory is found with
  `QStandardPaths` (`<data dir>/klipperqr/translations`, `/app/share/...`
  in the Flatpak), with the repository `translations/` folder as a fallback in
  a source checkout, like `find_qml_main()` does for QML.
- Do not add an in-app language picker now. If the Phase 4 settings page wants
  one, store a `language` key in QSettings (tested to work, see log).
- Kirigami's own strings ("Close", "Back"...) come from KDE's catalogs in the
  runtime, selected by the process locale. Expected to work, not tested.

Why not gettext: it is the better fit for the KDE translator community, but
QML has no gettext support, so we would carry our own helper and extraction
step. For a small app with few strings, Qt tooling is the least code and
needs no extra tools. If KlipperQR ever goes to KDE review, converting `.ts`
to `.po` is mechanical (Qt's `lconvert` can do it, expected, not tested), and
because all strings are already wrapped, migration is cheap.

**Settings: `QSettings`**, with `QCoreApplication.setOrganizationName(...)` and
`setApplicationName(...)` set once in `main.py`.

- Wrap it in a Python `QObject` (Phase 4) so QML never touches files.
- Organization name: for the real app use a value consistent with the app id
  `io.github.octaviobernal` (decide in Phase 4; it becomes part of the file path).
- Never store clipboard text, or anything derived from it, in settings.
- No extra Flatpak permission is needed.
- Not planned: KConfig integration, because there are no PySide6 bindings.

## How a contributor runs it

Needs only PySide6 (already in `requirements.txt`).

```sh
# 1. Update the catalog after adding or changing strings (from the repo root).
#    Run this for each language file; new languages: add -ts translations/klipperqr_<lang>.ts
pyside6-lupdate qml/*.qml src/klipperqr/*.py -ts translations/klipperqr_es.ts

# 2. Translate: open the .ts in Qt Linguist (pyside6-linguist), or edit the XML.

# 3. Compile to the binary .qm that the app loads.
pyside6-lrelease translations/klipperqr_es.ts -qm build/klipperqr_es.qm
```

Proposed follow-up work (belongs to the Phase 3 translation issue, not this
spike): create `translations/`, load the translator in `main.py`, install
`.qm` files in the Flatpak manifest (`pyside6-lrelease` being available at
build time in the SDK/BaseApp is expected, not tested; committing generated
`.qm` files is a fallback we would prefer to avoid), and add a check that `.ts` files are up to
date.

Try the spike yourself:

```sh
mkdir -p /tmp/i18n
pyside6-lrelease docs/spike-i18n/klipperqr_es.ts -qm /tmp/i18n/klipperqr_es.qm
KLIPPERQR_LANG=es python3 docs/spike-i18n/poc_i18n.py /tmp/i18n          # opens a window
KLIPPERQR_LANG=es python3 docs/spike-i18n/poc_i18n.py /tmp/i18n --print  # prints the label texts
```

## Verification log (2026-10-17)

- `pyside6-lupdate Poc.qml poc_i18n.py` found all 4 strings: 3 from QML
  (including a plural with `//:` note) and 1 from Python (`self.tr`).
- `pyside6-lrelease` compiled 4 translations.
- Host, `KLIPPERQR_LANG=es`: labels read "Pegar desde el portapapeles",
  "3 caracteres", "Mensaje desde Python". With `en`: the English source
  strings and no translator loaded. The window title was not read back.
- Host, no env var: the language stored with `QSettings` (`language=es`) was
  picked up on the next start, and `lastTestRun` was written. The file was `[General]` INI.
- Flatpak (`flatpak run --command=python3` of the existing build, offscreen,
  `KLIPPERQR_LANG=es`): the same three Spanish texts, and the settings file was
  created at `~/.var/app/io.github.octaviobernal.KlipperQR/config/KlipperQRSpike/klipperqr-spike.conf`.
  The test file was deleted afterwards. The command was run from the host path
  with `--filesystem` for the test folders, which is only for the spike; the
  real app will not need it.
- In the Flatpak run, QML printed "Cannot read property 'message' of null" warnings
  at exit (the Python backend object was released before the QML window);
  cosmetic for the throwaway script, the label values were correct.

## Risks

1. **Non-standard KDE workflow.** KDE's translation teams work with gettext
   PO files; a `.ts` catalog will not be picked up by KDE's l10n scripts
   automatically. Fine for a standalone Flathub app (Weblate/Transifex or
   direct pull requests work), a task to redo if the app joins KDE review.
2. **Translators must learn `.ts`.** Mitigation: Qt Linguist, Weblate, or
   `lconvert` to PO (expected, not tested).
3. **`.qm` files are build output.** The Flatpak build must run
   `pyside6-lrelease` or the app ships English only; a missing translation fails silently.
4. **Python extraction limits.** `pyside6-lupdate` only extracts string
   literals; `self.tr(variable)` or text built by concatenation is missed.
   Use plain literals and `%1`/`%n` placeholders.
5. **Mixed catalogs.** Kirigami strings use KDE catalogs, ours use Qt's; they
   follow the same locale, but a language missing in one will mix with English.
6. **QSettings path depends on organization and application name.** Changing
   them later moves the file and loses users' settings (migration needed).
7. **Language picker.** Switching language at runtime needs
   `engine.retranslate()`; not tested. Plan on follow-the-system-locale only.

## Needs a human

- Look at the window on screen with `KLIPPERQR_LANG=es` (only offscreen was run).
- Confirm the Flathub/KDE translator preference (Qt `.ts` vs gettext) is acceptable to you.
