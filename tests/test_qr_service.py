# SPDX-FileCopyrightText: 2026 Octavio Bernal <octavio.bernal.q@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import base64
import io
import re
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import segno  # noqa: E402

from klipperqr import qr_service  # noqa: E402
from klipperqr.qr_service import (  # noqa: E402
    DENSE_THRESHOLD_CHARS,
    QrResult,
    QrService,
    QrState,
    generate_qr,
)

SECRET = "s3cr3t-clipboard-text-é€"
URL = "https://kde.org/plasma-desktop/"


def _png_pixels(png: bytes):
    """Decode the PNG with Qt (already a dependency). Returns rows of (r, g, b)
    tuples and the set of colours used."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    image = QImage.fromData(png, "PNG")
    assert not image.isNull()
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    rows = []
    for y in range(image.height()):
        row = []
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            row.append((c.red(), c.green(), c.blue()))
        rows.append(row)
    return rows, {c for r in rows for c in r}


def _modules_from_png(result: QrResult):
    """Return rows of booleans (True = dark) per module incl. quiet zone."""
    rows, palette = _png_pixels(result.png)
    scale = qr_service.SCALE
    out = []
    for y in range(0, len(rows), scale):
        out.append([rows[y][x] == (0, 0, 0) for x in range(0, len(rows[0]), scale)])
    return out


def _expected_modules(text: str, level: str = "m"):
    q = segno.make(text, error=level, micro=False, boost_error=False, encoding="utf-8")
    border = qr_service.QUIET_ZONE_MODULES
    size = len(q.matrix) + 2 * border
    grid = [[False] * size for _ in range(size)]
    for y, row in enumerate(q.matrix):
        for x, v in enumerate(row):
            grid[y + border][x + border] = bool(v)
    return grid, q


# --- OK result -------------------------------------------------------------


def test_ok_result_has_png_and_svg():
    r = generate_qr(URL)
    assert r.state == QrState.OK
    assert r.png.startswith(b"\x89PNG\r\n\x1a\n")
    assert r.svg.lstrip().startswith("<?xml") and "<svg" in r.svg
    assert r.message == "" and r.dense is False


def test_png_and_svg_are_the_same_symbol_as_segno():
    r = generate_qr(URL)
    grid, _ = _expected_modules(URL)
    assert _modules_from_png(r) == grid
    # The SVG is a path in module units scaled by SCALE; compare its size.
    size = len(grid) * qr_service.SCALE
    assert f'width="{size}"' in r.svg and f'height="{size}"' in r.svg


def test_png_has_quiet_zone_and_only_black_on_white():
    r = generate_qr(URL)
    rows, palette = _png_pixels(r.png)
    assert palette == {(0, 0, 0), (255, 255, 255)}
    border_px = 4 * qr_service.SCALE
    h, w = len(rows), len(rows[0])
    assert h == w
    white = (255, 255, 255)
    for y in range(h):
        for x in range(w):
            if (
                y < border_px
                or y >= h - border_px
                or x < border_px
                or x >= w - border_px
            ):
                assert rows[y][x] == white


def test_svg_has_explicit_white_background_and_black_modules():
    svg = generate_qr(URL).svg
    assert re.search(r'<path fill="#fff" d="M0 0h(\d+)v\1h-\1z"', svg)
    assert 'stroke="#000"' in svg
    # Quiet zone: the dark path starts at module 4, background covers all.
    _, q = _expected_modules(URL)
    total = len(q.matrix) + 8
    assert f"M0 0h{total}v{total}h-{total}z" in svg
    assert re.search(r'd="M4 4\.5', svg)


# --- pitfalls from docs/qr-library.md ---------------------------------------


def test_no_micro_qr_for_tiny_text():
    r = generate_qr("1")
    grid, q = _expected_modules("1")
    assert not q.is_micro and q.version == 1
    assert len(grid) == 21 + 8  # version 1 is 21 modules, never 11 (M1)
    assert len(_modules_from_png(r)) == 29


def test_no_error_level_boost():
    # segno boosts a short URL from M to Q by default; we must not.
    r = generate_qr(URL, "M")
    grid, q = _expected_modules(URL, "m")
    assert q.error == "M"
    assert _modules_from_png(r) == grid
    boosted = segno.make(URL, error="m", micro=False, boost_error=True)
    assert boosted.error == "Q"
    assert _modules_from_png(r) != _expected_modules(URL, "q")[0]


def test_default_level_is_m():
    assert qr_service.DEFAULT_ERROR_LEVEL == "M"
    assert generate_qr(URL).png == generate_qr(URL, "M").png


@pytest.mark.parametrize("level", ["L", "M", "Q", "H", "l", "q"])
def test_all_levels_accepted_and_respected(level):
    r = generate_qr(URL, level)
    assert r.state == QrState.OK
    assert _modules_from_png(r) == _expected_modules(URL, level.lower())[0]


def test_levels_give_different_symbols():
    pngs = {generate_qr(URL, lv).png for lv in "LMQH"}
    assert len(pngs) == 4


@pytest.mark.parametrize("level", ["X", "", "MM", None, 3])
def test_invalid_level_is_failed_not_exception(level):
    r = generate_qr(URL, level)
    assert r.state == QrState.FAILED and r.message and not r.png


def test_text_is_encoded_as_utf8():
    text = "caf\u00e9"
    utf8 = segno.make(
        text.encode("utf-8"), error="m", micro=False, boost_error=False, mode="byte"
    )
    latin = segno.make(
        text, error="m", micro=False, boost_error=False, encoding="iso-8859-1"
    )
    ours = _modules_from_png(generate_qr(text))
    assert ours == _expected_modules(text)[0]
    assert ours == [[bool(v) for v in r] for r in _with_border(utf8)]
    assert ours != [[bool(v) for v in r] for r in _with_border(latin)]


def _with_border(q):
    n = len(q.matrix) + 8
    grid = [[False] * n for _ in range(n)]
    for y, row in enumerate(q.matrix):
        for x, v in enumerate(row):
            grid[y + 4][x + 4] = bool(v)
    return grid


# --- states ---------------------------------------------------------------


def test_empty_text():
    r = generate_qr("")
    assert r.state == QrState.EMPTY
    assert r.png == b"" and r.svg == "" and r.dense is False


def test_non_string_is_empty_not_exception():
    assert generate_qr(None).state == QrState.EMPTY


def test_boundary_level_m_ascii():
    assert generate_qr("a" * 2331).state == QrState.OK
    r = generate_qr("a" * 2332)
    assert r.state == QrState.TOO_LONG
    assert r.png == b"" and r.svg == ""
    assert r.message and "too long" in r.message.lower()


def test_boundaries_other_levels():
    for level, cap in (("L", 2953), ("Q", 1663), ("H", 1273)):
        assert generate_qr("a" * cap, level).state == QrState.OK
        assert generate_qr("a" * (cap + 1), level).state == QrState.TOO_LONG


def test_very_long_text_is_too_long():
    r = generate_qr("x" * 100_000)
    assert r.state == QrState.TOO_LONG and r.message and r.dense is True


def test_unicode_capacity_boundary():
    assert generate_qr("é" * 1165).state == QrState.OK
    assert generate_qr("é" * 1166).state == QrState.TOO_LONG


def test_long_and_unicode_text_roundtrip_structure():
    for text in ("€é中文 \U0001f600 line1\nline2\ttab", "x" * 1500):
        r = generate_qr(text)
        assert r.state == QrState.OK
        assert _modules_from_png(r) == _expected_modules(text)[0]


def test_whitespace_only_text_is_encoded():
    assert generate_qr(" ").state == QrState.OK


def test_lone_surrogate_is_failed_without_exception():
    r = generate_qr("bad \ud800 text")
    assert r.state == QrState.FAILED and r.message
    assert "bad" not in r.message.split("from this")[0]
    assert "\ud800" not in r.message


def test_unexpected_exception_is_failed_and_hides_details(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(qr_service.segno, "make", boom)
    r = generate_qr(SECRET)
    assert r.state == QrState.FAILED
    assert SECRET not in r.message and SECRET not in repr(r)
    assert r.png == b"" and r.svg == ""


def test_failure_while_saving_is_failed(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError(SECRET)

    monkeypatch.setattr(qr_service, "_save", boom)
    assert generate_qr(SECRET).state == QrState.FAILED


def test_optional_real_decoder_roundtrip():
    zxingcpp = pytest.importorskip("zxingcpp")
    PIL_Image = pytest.importorskip("PIL.Image")
    for text in (URL, "café €", "x" * 1000):
        img = PIL_Image.open(io.BytesIO(generate_qr(text).png))
        assert [b.text for b in zxingcpp.read_barcodes(img)] == [text]


# --- dense flag -----------------------------------------------------------


def test_dense_threshold_constant_is_1000():
    assert DENSE_THRESHOLD_CHARS == 1000


def test_dense_flag_boundary():
    assert generate_qr("a" * 1000).dense is False
    r = generate_qr("a" * 1001)
    assert r.state == QrState.OK and r.dense is True


def test_dense_follows_the_constant(monkeypatch):
    monkeypatch.setattr(qr_service, "DENSE_THRESHOLD_CHARS", 5)
    assert generate_qr("abcdef").dense is True
    assert generate_qr("abcde").dense is False


# --- privacy ----------------------------------------------------------------


def test_repr_has_no_text_or_data():
    r = generate_qr(SECRET)
    assert SECRET not in repr(r) and "PNG" not in repr(r)
    assert SECRET not in repr(QrService())


def test_result_does_not_contain_text():
    r = generate_qr(SECRET)
    assert SECRET not in r.svg
    assert SECRET not in r.message


def test_no_output_and_no_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    generate_qr(SECRET)
    generate_qr("a" * 5000)
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""
    assert list(tmp_path.iterdir()) == []


def test_no_logging_or_io_in_module():
    source = Path(qr_service.__file__).read_text()
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    for word in (
        "print(",
        "import logging",
        "QSettings",
        "open(",
        "write_text",
        "tempfile",
    ):
        assert word not in code


def test_no_logging_records(caplog):
    with caplog.at_level("DEBUG"):
        generate_qr(SECRET)
        generate_qr("a" * 5000)
    assert caplog.records == []


def test_service_has_no_attribute_holding_text():
    s = QrService()
    s.generate(SECRET)
    for value in vars(s).values():
        assert value != SECRET
    assert SECRET not in repr(vars(s))


# --- QrService (QML-facing) ---------------------------------------------------


@pytest.fixture
def service():
    return QrService()


def test_service_starts_empty(service):
    assert service.state == QrState.EMPTY
    assert service.pngDataUrl == "" and service.svg == "" and not service.dense
    assert service.png.size() == 0 and service.message == ""


def test_service_generate_and_signal(service):
    seen = []
    service.resultChanged.connect(lambda: seen.append(1))
    service.generate(URL)
    assert seen == [1]
    assert service.state == QrState.OK
    assert service.png.data() == generate_qr(URL).png
    assert service.svg == generate_qr(URL).svg
    url = service.pngDataUrl
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == generate_qr(URL).png


def test_service_level_argument(service):
    service.generate(URL, "H")
    assert service.png.data() == generate_qr(URL, "H").png


def test_service_change_and_clear(service):
    service.generate(URL)
    first = service.pngDataUrl
    service.generate("other")
    assert service.pngDataUrl != first
    service.clear()
    assert service.state == QrState.EMPTY and service.pngDataUrl == ""
    service.generate(URL)
    service.generate("")
    assert service.state == QrState.EMPTY and service.pngDataUrl == ""


def test_service_too_long_and_dense(service):
    service.generate("a" * 3000)
    assert service.state == QrState.TOO_LONG
    assert service.message and service.pngDataUrl == "" and service.dense
    service.generate("a" * 1500)
    assert service.state == QrState.OK and service.dense and service.message == ""
    assert service.denseThreshold == 1000


def test_service_enum_matches_state():
    for name in ("OK", "EMPTY", "TOO_LONG", "FAILED"):
        assert int(getattr(QrService.State, name)) == int(getattr(QrState, name))


def test_qml_property_access():
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlEngine()
    service = QrService()
    engine.rootContext().setContextProperty("qrService", service)
    comp = QQmlComponent(engine)
    comp.setData(
        b"import QtQml\nimport KlipperQR\nQtObject {\n"
        b"  property bool ok: qrService.state === QrService.State.OK\n"
        b"  property string url: qrService.pngDataUrl\n"
        b"  property bool dense: qrService.dense\n"
        b"  function run(t) { qrService.generate(t) }\n}\n",
        QUrl(),
    )
    obj = comp.create()
    assert obj is not None, comp.errorString()
    assert obj.property("ok") is False
    obj.run("hello")
    assert obj.property("ok") is True
    assert obj.property("url").startswith("data:image/png;base64,")
    assert app is not None and isinstance(obj, QObject)


# --- Saving to a file (issue #28) -------------------------------------------


def test_save_png_and_svg_to_temp_dir(tmp_path):
    from PySide6.QtCore import QUrl

    service = QrService()
    service.generate(URL)
    png = tmp_path / "qrcode.png"
    svg = tmp_path / "qrcode.svg"
    assert service.saveToFile(QUrl.fromLocalFile(str(png)), "png") is True
    assert service.saveToFile(QUrl.fromLocalFile(str(svg)), "svg") is True
    assert png.read_bytes() == service.png.data()
    assert png.read_bytes().startswith(b"\x89PNG")
    text = svg.read_text(encoding="utf-8")
    assert text == service.svg and "<svg" in text
    assert URL not in text


def test_save_without_suffix_uses_chosen_kind(tmp_path):
    result = generate_qr(URL)
    assert qr_service.save_qr(result, tmp_path / "plain", "svg") is True
    assert (tmp_path / "plain.svg").is_file()
    assert qr_service.save_qr(result, tmp_path / "other.PNG", "svg") is True
    assert (tmp_path / "other.PNG").read_bytes() == result.png


def test_save_failures_return_false_without_raising(tmp_path):
    from PySide6.QtCore import QUrl

    service = QrService()
    # No QR yet.
    assert (
        service.saveToFile(QUrl.fromLocalFile(str(tmp_path / "a.png")), "png") is False
    )
    assert not (tmp_path / "a.png").exists()
    service.generate(URL)
    # Missing folder, and a non-local URL.
    missing = tmp_path / "nope" / "a.png"
    assert service.saveToFile(QUrl.fromLocalFile(str(missing)), "png") is False
    assert service.saveToFile(QUrl("https://example.org/a.png"), "png") is False
    assert qr_service.save_qr(generate_qr(URL), tmp_path / "x", "bmp") is False
