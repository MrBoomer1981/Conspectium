"""Image compression — app/services/images.py.

Inviolable rule 2 in CLAUDE.md: the long side is capped at 1500 px and the
result is JPEG. A full-size phone photo costs several times more with no gain
in accuracy, so a regression here is a regression in the bill.
"""

import io

from PIL import Image

from app.services import images


def _jpeg(width: int, height: int, mode: str = "RGB", exif: bytes | None = None) -> bytes:
    img = Image.new(mode, (width, height), color="white" if mode != "P" else 1)
    buf = io.BytesIO()
    if mode in ("RGBA", "P"):
        img.save(buf, format="PNG")
    else:
        img.save(buf, format="JPEG", **({"exif": exif} if exif else {}))
    return buf.getvalue()


def _size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as img:
        return img.size


def test_long_side_is_capped_at_1500():
    result = images.compress(_jpeg(3000, 2000))
    assert max(_size(result)) == 1500


def test_aspect_ratio_is_preserved():
    result = images.compress(_jpeg(3000, 2000))
    assert _size(result) == (1500, 1000)


def test_portrait_orientation_caps_the_height():
    result = images.compress(_jpeg(2000, 4000))
    assert _size(result) == (750, 1500)


def test_smaller_images_are_never_upscaled():
    result = images.compress(_jpeg(800, 600))
    assert _size(result) == (800, 600)


def test_image_exactly_at_the_cap_is_left_alone():
    result = images.compress(_jpeg(1500, 1000))
    assert _size(result) == (1500, 1000)


def test_output_is_always_jpeg():
    with Image.open(io.BytesIO(images.compress(_jpeg(200, 200)))) as img:
        assert img.format == "JPEG"


def test_rgba_is_converted_to_rgb():
    # JPEG cannot hold an alpha channel: without the conversion this raises.
    with Image.open(io.BytesIO(images.compress(_jpeg(200, 200, mode="RGBA")))) as img:
        assert img.mode == "RGB"


def test_palette_mode_is_converted_to_rgb():
    with Image.open(io.BytesIO(images.compress(_jpeg(200, 200, mode="P")))) as img:
        assert img.mode == "RGB"


def test_max_side_is_configurable():
    result = images.compress(_jpeg(3000, 2000), max_side=600)
    assert max(_size(result)) == 600


def test_lower_quality_produces_a_smaller_file():
    # Guards the quality argument actually reaching the encoder.
    source = _jpeg(1000, 1000)
    assert len(images.compress(source, quality=20)) < len(
        images.compress(source, quality=95)
    )


def test_exif_orientation_is_applied():
    """Orientation 6 means "rotate 90°". A phone shot in portrait arrives as a
    landscape frame plus this tag; ignoring it feeds the model a sideways page.
    """
    exif = Image.Exif()
    exif[274] = 6  # 274 = Orientation
    portrait_stored_as_landscape = _jpeg(1000, 500, exif=exif.tobytes())

    result = images.compress(portrait_stored_as_landscape)

    # exif_transpose swaps the axes, so what was 1000x500 comes back 500x1000.
    assert _size(result) == (500, 1000)


def test_image_without_exif_keeps_its_orientation():
    assert _size(images.compress(_jpeg(1000, 500))) == (1000, 500)
