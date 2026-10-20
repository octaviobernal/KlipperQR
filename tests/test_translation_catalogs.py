# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""scripts/check-translations.py: passes on a clean tree, fails on a new string.

The script is run against a scratch copy of the repository, so the real
files are never touched.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    shutil.which("pyside6-lupdate") is None, reason="pyside6-lupdate not found"
)


@pytest.fixture
def scratch_repo(tmp_path):
    for folder in ("qml", "src", "translations", "scripts"):
        shutil.copytree(
            ROOT / folder,
            tmp_path / folder,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    return tmp_path


def check(repo):
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "check-translations.py")],
        capture_output=True,
        text=True,
    )


def test_clean_tree_passes(scratch_repo):
    result = check(scratch_repo)
    assert result.returncode == 0, result.stderr


def test_moved_code_only_changing_line_numbers_passes(scratch_repo):
    main_qml = scratch_repo / "qml" / "Main.qml"
    main_qml.write_text("\n\n" + main_qml.read_text(encoding="utf-8"), encoding="utf-8")
    assert check(scratch_repo).returncode == 0


def test_new_string_fails_and_names_the_command(scratch_repo):
    main_qml = scratch_repo / "qml" / "Main.qml"
    text = main_qml.read_text(encoding="utf-8")
    main_qml.write_text(
        text.replace("{", '{\n    property string t: qsTr("Zzz new")', 1),
        encoding="utf-8",
    )
    result = check(scratch_repo)
    assert result.returncode == 1
    assert "check-translations.py --update" in result.stderr
    assert "Zzz new" in result.stderr


def test_update_flag_fixes_a_stale_catalog(scratch_repo):
    main_qml = scratch_repo / "qml" / "Main.qml"
    text = main_qml.read_text(encoding="utf-8")
    main_qml.write_text(
        text.replace("{", '{\n    property string t: qsTr("Zzz new")', 1),
        encoding="utf-8",
    )
    script = scratch_repo / "scripts" / "check-translations.py"
    subprocess.run([sys.executable, str(script), "--update"], check=True)
    assert check(scratch_repo).returncode == 0
