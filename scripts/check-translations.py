#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Check that translations/*.ts match the strings in the source code.

How: copy qml/, src/ and translations/ to a temporary folder, run
`pyside6-lupdate` there on every catalog, and compare each result with the
committed file. <location> lines (file and line numbers) are ignored, so
moving code around does not fail the check; added, removed or changed
strings do. Nothing in the repository is modified unless --update is given.
Compiling .qm files is not part of this check.

Usage (from anywhere):
    python3 scripts/check-translations.py            # check, exit 1 if stale
    python3 scripts/check-translations.py --update   # rewrite the catalogs
"""

import argparse
import difflib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["qml/*.qml", "src/klipperqr/*.py"]
LOCATION = re.compile(r"^\s*<location [^>]*/>\s*$")


def run_lupdate(base: Path, ts_files: list[Path]) -> None:
    """Run pyside6-lupdate in `base` on each catalog (paths relative to base)."""
    exe = shutil.which("pyside6-lupdate")
    if exe is None:
        sys.exit(
            "ERROR: pyside6-lupdate not found (pip install -r requirements-dev.txt)"
        )
    files = sorted(
        p.relative_to(base).as_posix() for s in SOURCES for p in base.glob(s)
    )
    for ts in ts_files:
        subprocess.run(
            [exe, *files, "-ts", ts.relative_to(base).as_posix()],
            cwd=base,
            check=True,
            capture_output=True,
        )


def normalized(path: Path) -> list[str]:
    return [
        ln
        for ln in path.read_text(encoding="utf-8").splitlines()
        if not LOCATION.match(ln)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--update", action="store_true", help="rewrite the catalogs")
    args = parser.parse_args()

    catalogs = sorted((ROOT / "translations").glob("klipperqr_*.ts"))
    if not catalogs:
        print("ERROR: no translations/klipperqr_*.ts found", file=sys.stderr)
        return 1

    if args.update:
        run_lupdate(ROOT, catalogs)
        print(f"Updated {len(catalogs)} catalog(s).")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for folder in ("qml", "src", "translations"):
            shutil.copytree(
                ROOT / folder,
                work / folder,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        run_lupdate(work, [work / "translations" / c.name for c in catalogs])

        stale = False
        for cat in catalogs:
            old = normalized(cat)
            new = normalized(work / "translations" / cat.name)
            if old != new:
                stale = True
                print(f"STALE: translations/{cat.name}", file=sys.stderr)
                diff = difflib.unified_diff(
                    old, new, "committed", "expected", lineterm="", n=1
                )
                print("\n".join(list(diff)[:40]), file=sys.stderr)

    if stale:
        print(
            "\nThe translation catalogs are out of date. Run:\n"
            "    python3 scripts/check-translations.py --update\n"
            "(same as: pyside6-lupdate qml/*.qml src/klipperqr/*.py "
            "-ts translations/klipperqr_<lang>.ts for each catalog),\n"
            "translate any new strings, and commit the .ts files.",
            file=sys.stderr,
        )
        return 1
    print("Translation catalogs are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
