"""The two rules in photoguard this project has edited.

The module is otherwise imported and called, never touched, and it arrived
with its own tests that did not come with it. What is covered here is the two
changes and their neighbourhood.

The first: `_line_height` returns 0.0 when it could not measure at all — and
that used to be read as a measurement of a very small line, so a page written
large was refused as a page written small.

The second: how it measures at all. The tests below build pages whose line
pitch is known by construction and check the measurement against it, because
that is the only way to tell a working estimator from one that returns a
number.

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


def _written_page(
    pitch: int, lines: int, drawing: bool = False, ink: int = 60, paper: int = 235
) -> Image.Image:
    """A page of handwriting with a **known** line pitch.

    Ragged strokes rather than solid bars: a bar of constant width is read by
    any profile, and the estimator has to survive a line that starts and ends
    where the hand happened to stop.
    """
    from PIL import ImageDraw, ImageFilter

    rng = np.random.default_rng(7)
    image = Image.new("L", (1200, 1500), paper)
    draw = ImageDraw.Draw(image)
    for index in range(lines):
        top = 80 + index * pitch
        if top + pitch > 1440:
            break
        left = 90
        while left < 1080:
            width = int(rng.integers(pitch // 3, pitch))
            draw.line(
                [(left, top + pitch // 2), (left + width, top + int(rng.integers(0, pitch // 2)))],
                fill=ink,
                width=max(2, pitch // 10),
            )
            left += width + max(3, pitch // 6)
    if drawing:
        draw.ellipse([340, 980, 860, 1440], outline=ink, width=4)
        draw.line([340, 1210, 860, 1210], fill=ink, width=4)
    return image.filter(ImageFilter.GaussianBlur(1.0))


def _measured(image: Image.Image) -> float:
    """What _line_height says about the paper region of this page."""
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    top, left, bottom, right = photoguard._paper_box(gray)
    return photoguard._line_height(gray[top:bottom, left:right])


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


# ── how it measures, against a pitch that is known by construction ───────────


@pytest.mark.parametrize("pitch", [28, 40, 55, 120, 220])
def test_the_measured_pitch_is_the_pitch_that_was_drawn(pitch):
    """The claim the rewrite stands on. The old estimator answered 0.0 to every
    one of these: it thresholded ink at the 35th percentile of brightness,
    which on a page that is 5% ink lands on the paper, so the mask covered the
    whole sheet and the profile came out flat."""
    measured = _measured(_written_page(pitch=pitch, lines=1400 // pitch))

    assert measured == pytest.approx(pitch, rel=0.05)


def test_a_drawing_no_longer_stretches_the_measurement():
    """Height-over-count measures the page, not the line: a drawing or an empty
    margin inflates it by however large it is. On a page with a drawing the
    mean and the median ran 2.5 to 16 times apart, which is what the median is
    for."""
    measured = _measured(_written_page(pitch=120, lines=7, drawing=True))

    assert measured == pytest.approx(120, rel=0.05)


def test_pale_ink_and_a_dark_photograph_are_measured_the_same():
    # Otsu finds the valley between paper and ink wherever the two sit on the
    # scale; a rank threshold moves with how much ink the page carries.
    pale = _measured(_written_page(pitch=55, lines=22, ink=150, paper=225))
    dark = _measured(_written_page(pitch=55, lines=22, ink=20, paper=90))

    assert pale == pytest.approx(55, rel=0.05)
    assert dark == pytest.approx(55, rel=0.05)


def test_a_page_written_large_is_measured_rather_than_refused():
    """Five lines on a sheet used to be fewer than the three the old estimator
    demanded — no, fewer than it could resolve — and a page written large is
    exactly the page that carries few lines."""
    measured = _measured(_written_page(pitch=220, lines=5))

    assert measured > photoguard.MIN_LINE_HEIGHT_PX


def test_a_single_line_answers_with_its_own_height():
    """Not the sentinel: one band cannot give a pitch, but its own height is a
    lower bound on one, and a lower bound is what the threshold wants."""
    measured = _measured(_written_page(pitch=260, lines=1))

    assert measured > photoguard.MIN_LINE_HEIGHT_PX


def test_a_blank_page_is_still_unmeasured():
    assert _measured(_written_page(pitch=55, lines=0)) == (
        photoguard.UNMEASURED_LINE_HEIGHT
    )


def test_text_too_small_to_read_is_still_refused():
    """The rewrite must not cost the check its job: this is the page the whole
    module exists for, photographed from too far away."""
    # Darker ink than the other pages here, so that contrast — which is
    # checked first — passes and the line-height rule is the one deciding.
    verdict = photoguard._check(
        _written_page(pitch=15, lines=90, ink=10, paper=250)
    )

    assert verdict.line_height_px < photoguard.MIN_LINE_HEIGHT_PX
    assert verdict.ok is False
    assert "мелкий" in verdict.reason


def test_a_densely_written_page_is_read_rather_than_refused():
    """Record 45: a notebook written densely and sent through Telegram, which
    compresses a photo to 1280 px, measured 19.75 px on the page the old
    threshold of 20 cut off, while four pages of it at 22.75 px read well.
    Taken again from the same distance it would have measured the same."""
    verdict = photoguard._check(
        _written_page(pitch=19, lines=70, ink=10, paper=250)
    )

    assert verdict.line_height_px < 20
    assert verdict.ok, verdict.reason
