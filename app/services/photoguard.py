"""
Проверка фотографии ДО вызова модели.

Зачем. Модель не умеет сказать «я это не прочитала». На мелком,
смазанном или снятом издалека кадре она узнаёт тему по заголовку
и выдаёт правдоподобный пересказ из памяти, пометив его как
полностью прочитанный (unreadable_count: 0).

Единственная надёжная защита — не давать ей такой кадр.
Это классическая обработка изображения: быстро, бесплатно,
детерминированно. Никаких моделей.

Зависимости: Pillow, numpy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

# ─── Пороги. Подбираются на своих данных, это разумные стартовые ───

MIN_LINE_HEIGHT_PX = 20      # ниже — буквы мельче ~11 px, читать нечем
MIN_SHARPNESS      = 90.0    # дисперсия лапласиана в области листа
MIN_PAPER_FRACTION = 0.18    # лист меньше 18% кадра — снято издалека
MIN_CONTRAST       = 28.0    # стандартное отклонение яркости на листе


@dataclass
class PhotoVerdict:
    ok: bool
    reason: str                  # что сказать пользователю
    line_height_px: float
    sharpness: float
    paper_fraction: float
    contrast: float

    def render(self) -> str:
        mark = "✅" if self.ok else "❌"
        return (
            f"{mark} {self.reason}\n"
            f"   высота строки : {self.line_height_px:5.1f} px  (нужно ≥ {MIN_LINE_HEIGHT_PX})\n"
            f"   резкость      : {self.sharpness:5.0f}     (нужно ≥ {MIN_SHARPNESS:.0f})\n"
            f"   лист в кадре  : {self.paper_fraction*100:5.0f} %     (нужно ≥ {MIN_PAPER_FRACTION*100:.0f} %)\n"
            f"   контраст      : {self.contrast:5.1f}     (нужно ≥ {MIN_CONTRAST:.0f})"
        )


def _laplacian_var(gray: np.ndarray) -> float:
    """Дисперсия лапласиана — классическая мера резкости.

    У смазанного изображения нет резких перепадов яркости,
    поэтому вторая производная близка к нулю везде.
    """
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    h, w = gray.shape
    if h < 3 or w < 3:
        return 0.0
    win = np.lib.stride_tricks.sliding_window_view(gray, (3, 3))
    lap = np.einsum("ijkl,kl->ij", win, k)
    return float(lap.var())


def _paper_box(gray: np.ndarray) -> tuple[int, int, int, int]:
    """Прямоугольник самой светлой области — предположительно лист.

    Порог берём от яркости, а не от доли пикселей: если лист занимает
    малую часть кадра, перцентильный порог уедет на фон и вернёт весь
    кадр целиком — ровно тот случай, который мы и ловим.
    99-й перцентиль вместо максимума — защита от одиночного блика.
    """
    thr = 0.82 * float(np.percentile(gray, 99))
    mask = gray >= thr
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if not len(rows) or not len(cols):
        return 0, 0, gray.shape[0], gray.shape[1]
    return int(rows[0]), int(cols[0]), int(rows[-1]) + 1, int(cols[-1]) + 1


def _line_height(region: np.ndarray) -> float:
    """Оценить высоту строки по горизонтальному профилю тёмных пикселей.

    Строки текста дают чередование «есть чернила / нет чернил».
    Считаем переходы — получаем число строк, делим высоту.
    """
    if region.size == 0:
        return 0.0
    thr = np.percentile(region, 35)
    ink = (region <= thr).sum(axis=1).astype(np.float32)
    if ink.max() == 0:
        return 0.0
    ink = ink / ink.max()
    # сглаживание, чтобы не считать шум за строки
    k = np.ones(3) / 3
    ink = np.convolve(ink, k, mode="same")
    active = ink > ink.mean()
    transitions = int(np.count_nonzero(active[1:] != active[:-1]))
    n_lines = transitions // 2
    if n_lines < 3:
        # Строк не видно вовсе — либо это не текст, либо он слишком мелкий,
        # чтобы дать различимый профиль. И то и другое = кадр не годится.
        return 0.0
    return float(region.shape[0] / n_lines)


def check_photo(path: str) -> PhotoVerdict:
    """Проверить фотографию по пути к файлу."""
    return _check(Image.open(path))


def _check(image: Image.Image) -> PhotoVerdict:
    img = ImageOps.exif_transpose(image).convert("L")
    gray = np.asarray(img, dtype=np.float32)

    r0, c0, r1, c1 = _paper_box(gray)
    paper = gray[r0:r1, c0:c1]
    paper_fraction = paper.size / gray.size

    sharpness = _laplacian_var(paper)
    contrast = float(paper.std())
    line_h = _line_height(paper)

    # Порядок проверок = порядок, в котором стоит жаловаться пользователю
    if paper_fraction < MIN_PAPER_FRACTION:
        ok, reason = False, "Лист занимает мало кадра — подойдите ближе"
    elif sharpness < MIN_SHARPNESS:
        ok, reason = False, "Фото смазано — переснимите, держа телефон неподвижно"
    elif contrast < MIN_CONTRAST:
        ok, reason = False, "Слишком темно или блик — добавьте света"
    elif line_h < MIN_LINE_HEIGHT_PX:
        ok, reason = False, "Текст мелкий — снимите одну страницу крупным планом"
    else:
        ok, reason = True, "Фото годится для распознавания"

    return PhotoVerdict(ok, reason, line_h, sharpness, paper_fraction, contrast)


def check_photo_bytes(data: bytes) -> PhotoVerdict:
    """То же, что check_photo, но из байтов — без временного файла.

    Нужно для бота: изображение приходит в память, писать его на диск
    только ради проверки незачем.
    """
    import io
    return _check(Image.open(io.BytesIO(data)))


# ─────────────────────────────────────────────────────────────
# Запуск из командной строки
#
#   python3 photoguard.py фото.jpg
#   python3 photoguard.py папка_с_фото/
#   python3 photoguard.py *.jpg
# ─────────────────────────────────────────────────────────────

def _iter_paths(args: list[str]):
    import os
    exts = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".tif", ".tiff"}
    for a in args:
        if os.path.isdir(a):
            for name in sorted(os.listdir(a)):
                if os.path.splitext(name)[1].lower() in exts:
                    yield os.path.join(a, name)
        else:
            yield a


def main(argv: list[str]) -> int:
    import os
    import sys

    if not argv:
        print(__doc__)
        print("Использование:")
        print("  python3 photoguard.py фото.jpg")
        print("  python3 photoguard.py папка_с_фото/")
        return 1

    paths = list(_iter_paths(argv))
    if not paths:
        print("Не нашёл ни одного изображения по указанному пути.")
        return 1

    passed = 0
    for p in paths:
        print("─" * 66)
        print(os.path.basename(p))
        try:
            v = check_photo(p)
        except Exception as exc:
            print(f"❌ Не смог открыть файл: {exc}")
            continue
        print(v.render())
        passed += v.ok

    print("─" * 66)
    print(f"Годных кадров: {passed} из {len(paths)}")
    if passed < len(paths):
        print("\nПодсказка: если вердикт расходится с твоим впечатлением —")
        print("подкрути пороги в начале photoguard.py и прогони заново.")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
