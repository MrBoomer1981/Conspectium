"""Image compression before sending to the model."""

import io

from PIL import Image, ImageOps


def compress(image_bytes: bytes, max_side: int = 1500, quality: int = 85) -> bytes:
    """Resize by the long side and re-encode as JPEG.

    Honors EXIF orientation. Never upscales an image already smaller than
    max_side.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")

        long_side = max(img.size)
        if long_side > max_side:
            scale = max_side / long_side
            new_size = (round(img.width * scale), round(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
