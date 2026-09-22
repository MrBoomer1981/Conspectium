"""The one rule in photoguard this project has edited.

The module is otherwise imported and called, never touched, and it arrived
with its own tests that did not come with it. What is covered here is the
change and its neighbourhood: `_line_height` returns 0.0 when it could not
measure at all — a page of two lines of large writing, a sparse page, a page
that is mostly a drawing — and that used to be read as a measurement of a very
small line. A page written large was refused as a page written small.

Reproduced on the deployed bot, three times with byte-identical numbers:

    line height 0.0/20, sharpness 1737/90, paper 97%/18%, contrast 54.7/28

Sharpness nineteen times over its threshold, the page filling 97% of the
frame, contrast at twice what is asked — and refused for small text.
"""

import io

import numpy as np
import pytest
from PIL import Image

from app.services import photoguard


def _page(stroke: int = 11, pitch: int = 45, lines: int = 20) -> Image.Image:
    """A page that clears paper fraction, sharpness and contrast comfortably,
    so that only the line-height rule is left deciding."""
    array = np.full((1500, 1125), 245, dtype=np.uint8)
    for i in range(lines):
        top = 120 + i * pitch
        array[top : top + stroke, 90:1000] = 40
    return Image.fromarray(array, mode="L")


def _verdict(monkeypatch, line_height, image=None) -> photoguard.PhotoVerdict:
    monkeypatch.setattr(photoguard, "_line_height", lambda region: line_height)
    return photoguard._check(image or _page())


# ── the change ───────────────────────────────────────────────────────────────


def test_a_page_whose_lines_could_not_be_counted_is_not_refused(monkeypatch):
    verdict = _verdict(monkeypatch, photoguard.UNMEASURED_LINE_HEIGHT)

    assert verdict.ok
    assert verdict.line_height_px == photoguard.UNMEASURED_LINE_HEIGHT


def test_text_that_really_is_small_is_still_refused(monkeypatch):
    # The rule has a job: a page in frame, sharp and well lit, written too
    # small for anything to be read off it.
    verdict = _verdict(monkeypatch, photoguard.MIN_LINE_HEIGHT_PX - 1)

    assert not verdict.ok
    assert "мелкий" in verdict.reason


def test_the_threshold_itself_passes(monkeypatch):
    assert _verdict(monkeypatch, float(photoguard.MIN_LINE_HEIGHT_PX)).ok


def test_the_sentinel_is_the_value_the_function_actually_returns():
    """The constant and the function have to agree, or the rule reads a
    measurement that never occurs and the refusal comes back."""
    blank = np.full((400, 400), 245, dtype=np.float32)
    assert photoguard._line_height(blank) == photoguard.UNMEASURED_LINE_HEIGHT
    assert photoguard._line_height(np.zeros((0, 0), dtype=np.float32)) == (
        photoguard.UNMEASURED_LINE_HEIGHT
    )


def test_a_page_of_two_large_lines_is_not_counted_as_small_text():
    # The shape that bit us, through the real function rather than a stub:
    # too few lines to build a profile from.
    verdict = photoguard._check(_page(stroke=46, pitch=150, lines=2))

    assert verdict.ok, verdict.render()


# ── the three rules that still decide ────────────────────────────────────────


def test_the_other_checks_still_refuse_whatever_the_line_height(monkeypatch):
    # Letting an unmeasured height through must not let anything else through
    # with it: those three are what stood between us and the retelling of a
    # page photographed from across the room.
    monkeypatch.setattr(
        photoguard, "_line_height", lambda region: photoguard.UNMEASURED_LINE_HEIGHT
    )

    blurred = Image.fromarray(
        np.full((1500, 1125), 245, dtype=np.uint8), mode="L"
    )
    verdict = photoguard._check(blurred)

    assert not verdict.ok
    assert verdict.sharpness < photoguard.MIN_SHARPNESS


def test_the_order_of_complaints_is_unchanged(monkeypatch):
    # paper fraction, then sharpness, then contrast, then line height. The
    # album log names the refusing check by recomputing it in this order.
    monkeypatch.setattr(photoguard, "_line_height", lambda region: 1.0)
    monkeypatch.setattr(photoguard, "_laplacian_var", lambda region: 1.0)

    verdict = photoguard._check(_page())

    assert "смазано" in verdict.reason  # sharpness wins over line height


# ── what the CLI prints, since step B will be calibrated on it ───────────────


def test_an_unmeasured_height_is_printed_as_unmeasured():
    verdict = photoguard.PhotoVerdict(
        ok=True,
        reason="Фото годится для распознавания",
        line_height_px=photoguard.UNMEASURED_LINE_HEIGHT,
        sharpness=1737.0,
        paper_fraction=0.97,
        contrast=54.7,
    )

    line = next(l for l in verdict.render().splitlines() if "высота строки" in l)
    assert "не измерена" in line
    assert "нужно" not in line  # there is no threshold to have missed


def test_a_measured_height_is_printed_against_its_threshold():
    verdict = photoguard.PhotoVerdict(
        ok=False,
        reason="Текст мелкий — снимите одну страницу крупным планом",
        line_height_px=8.3,
        sharpness=6965.0,
        paper_fraction=1.0,
        contrast=85.1,
    )

    line = next(l for l in verdict.render().splitlines() if "высота строки" in l)
    assert "8.3" in line
    assert str(photoguard.MIN_LINE_HEIGHT_PX) in line


def test_check_photo_bytes_is_the_entry_point_the_bot_uses():
    buffer = io.BytesIO()
    _page().convert("RGB").save(buffer, format="JPEG", quality=85)

    verdict = photoguard.check_photo_bytes(buffer.getvalue())

    assert isinstance(verdict, photoguard.PhotoVerdict)
