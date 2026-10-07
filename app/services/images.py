"""Image compression before sending to the model, and the threads image work
runs on."""

import asyncio
import functools
import io
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageOps

# Image work — a page decoded and compressed, its frame checked, its drawings
# cut — runs on two threads of its own, however many pages an album holds.
# Fanned over the default pool it ran a thread a page, ten at once, and on
# Linux each thread keeps an arena of the memory it peaked at: the process
# grew 50-100 MB an album and gave none of it back (task 76).
_WORKERS = ThreadPoolExecutor(max_workers=2, thread_name_prefix="images")


async def in_worker(work, /, *args):
    """`work(*args)` on the image threads, awaited — CPU work that would
    stall every chat on the event loop."""
    return await asyncio.get_running_loop().run_in_executor(
        _WORKERS, functools.partial(work, *args)
    )


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
