"""Image compression before sending to the model, a PDF's pages drawn as
pictures, and the threads image work runs on."""

import asyncio
import functools
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple

import numpy as np
import pypdfium2 as pdfium
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


# ── A PDF of notes (task 100) ────────────────────────────────────────────────
# Every page is drawn as a picture and read as an album's page, whatever the
# PDF holds: its text layer is no way in — a typed PDF's formulas come out of
# it flattened, and a scanner lays a junk reading of its own over handwriting.

# PDFium may not be called from two threads at once, not even over two
# documents, and image work runs on two: one PDF is opened and drawn at a time.
_PDFIUM = threading.Lock()

# A blank page — the back of a sheet in a scan, a page with nothing but its
# number — carries nothing of the lecture, and the frame check would refuse it
# as a blurred photograph. Ink is what is darker than this share of the
# paper's light; a page with less of it than _BLANK_INK of its area is blank.
_INK_OF_PAPER = 0.75
_BLANK_INK = 0.0005


class PdfPage(NamedTuple):
    number: int  # its place in the PDF, from 1: a blank page left out shifts none
    image: bytes  # compressed as a photograph is
    drawn: int  # bytes of the page as drawn, before compression
    width: int
    height: int


def pdf_page_count(data: bytes) -> int:
    """How many pages a PDF holds. Raises on a file PDFium cannot open — one
    broken, or locked by a password."""
    with _PDFIUM:
        document = pdfium.PdfDocument(data)
        try:
            return len(document)
        finally:
            document.close()


def pdf_pages(data: bytes, max_side: int = 1500, quality: int = 85) -> list[PdfPage]:
    """A PDF's pages as a photograph of each would be: drawn at `max_side` on
    the long side — the page's own rotation applied — and compressed as a
    photograph is (rule 2), a blank page left out. Raises as pdf_page_count
    does, and on a page PDFium cannot draw."""
    pages: list[PdfPage] = []
    with _PDFIUM:
        document = pdfium.PdfDocument(data)
        try:
            for index in range(len(document)):
                picture = _drawn(document, index, max_side)
                if _blank(picture):
                    continue
                buf = io.BytesIO()
                picture.save(buf, format="PNG")
                image = compress(buf.getvalue(), max_side, quality)
                pages.append(
                    PdfPage(index + 1, image, buf.tell(), picture.width, picture.height)
                )
        finally:
            document.close()
    return pages


def _drawn(document: pdfium.PdfDocument, index: int, max_side: int) -> Image.Image:
    """One page as a picture of its own. The page and its bitmap are closed
    here, under the lock, rather than by a finalizer on whichever thread the
    garbage collector runs: a copy of the picture outlives them."""
    page = document[index]
    try:
        width, height = page.get_size()
        bitmap = page.render(scale=max_side / max(width, height))
        try:
            return bitmap.to_pil().convert("RGB")
        finally:
            bitmap.close()
    finally:
        page.close()


def _blank(picture: Image.Image) -> bool:
    gray = np.asarray(picture.convert("L"), dtype=np.float32)
    paper = float(np.percentile(gray, 90))
    if paper <= 0:
        return False  # a black page is no blank paper: the frame check judges it
    ink = float((gray < paper * _INK_OF_PAPER).mean())
    return ink < _BLANK_INK
