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
#
# 2026-10-11 все четыре опущены по слову CEO («уменьши порог качества фото на
# всех параметрах», задача 102). Отмерено на трёх страницах записи 106 в
# 960×1280, как их присылает Telegram, испорченных нарочно — размытием,
# темнотой, засветкой, расстоянием — и прочитанных глазами по вырезкам из
# третьей; модель их не читала. Каждый порог стоит там, где текст ещё
# читается, с запасом до места, где индексы в формулах уже угадываются, а не
# читаются: на таком кадре модель дописывает их сама. Старые пороги отказывали
# страницам, которые читаются целиком.

MIN_LINE_HEIGHT_PX = 14      # ниже — буквы мельче ~6 px, читать нечем
# Единица не менялась при переписывании измерения: это по-прежнему шаг между
# строками в пикселях сжатого кадра (IMAGE_MAX_SIDE).
# Было 20. Запись 45 (2026-09-25): плотно исписанная тетрадь, снятая с одного
# расстояния, дала 22,75 px на четырёх страницах — они прочитались — и
# 19,75 px на пятой, которую порог отрезал. Telegram присылает фото в 1280 px
# по длинной стороне, и плотный конспект при таком сжатии стоит у самой
# границы 20, а переснять его крупнее с того же расстояния нельзя.
# Было 16 (задача 43). Опущен меньше других, потому что граница здесь близко:
# страница записи 106, уменьшенная до шага строк ~16 px, ещё читается словами,
# но индексы в формулах уже пропали; при ~14 px слова угадываются с трудом,
# при ~13 px остаётся только смысл. На клетчатой бумаге правило не срабатывает
# вовсе: сетка закрашивает каждую строку пикселей, и все три страницы записи
# 106 дали одну полосу во весь лист, 1141–1256 px.
# _line_height не всегда может измерить: у страницы с двумя строками крупной
# формулы, у разреженной страницы, у страницы с рисунком профиль не даёт того,
# что можно посчитать. Функция говорит об этом этим значением — и это
# отсутствие измерения, а не маленькое измерение. Пока эти два случая были
# неразличимы, страница, написанная крупно, отбраковывалась как мелкая.
UNMEASURED_LINE_HEIGHT = 0.0
MIN_SHARPNESS      = 15.0    # дисперсия лапласиана в области листа
# Было 90. Мера падает от малейшей мягкости кадра: размытие σ = 1 px дало
# 66–103 на трёх страницах, и 90 отказывало одной из них, а другую пропускало
# на 92, хотя все три читаются целиком. σ 1,4 — 17–25, читается; σ 1,6 —
# 12–18; σ 2 — 7–9, слова читаются, индексы угадываются; σ 2,5 — 4–6, только
# смысл. 15 отказывает с σ 1,5–1,6. Смаз в одну сторону мера почти не видит:
# линии сетки вдоль смаза остаются резкими, и 17 px смаза по строке дали 252
# на кадре, где текст не читается, — старый порог его пропускал так же.
MIN_PAPER_FRACTION = 0.14    # лист меньше 14% кадра — снято издалека
# Было 0,18. Лист на 42 % ширины кадра (17 % площади) читается с индексами,
# на 36 % (13 %) индексы начинают пропадать, на 30 % (9 %) пропали, на 25 %
# (6 %) остаётся только смысл. Это крупный почерк: мелкий теряется раньше, а
# высота строки на клетчатой бумаге его не ловит, так что этот порог опущен
# меньше других.
MIN_CONTRAST       = 10.0    # стандартное отклонение яркости на листе
# Было 28. 2026-10-07: вторая страница альбома, резкая (1337–1636 при нужных
# 90) и во весь кадр (91–100 %), трижды получила «Слишком темно» — 26,1, 26,4
# и 27,8. Разброс яркости по листу зависит не только от света, но и от того,
# сколько на странице написано: где строк мало, лист почти весь — ровная
# бумага, и разброс мал при любом освещении, а пересъёмка меряет то же самое.
# Порог поставлен ниже самой низкой хорошей страницы с запасом, как высота
# строки в задаче 43, — то есть откалиброван только сверху.
# Было 20. Страница при половине света дала 18,6–22,6 — 20 отказывало двум
# из трёх, — при четверти 10,0–13,3, и читается; при 0,18 света — 6,7–8,4,
# читается, но темно. Засвеченная до 30 % своей глубины — 11,9–17,4,
# читается; до 20 % — 7,7–11,4, бледно, индексы трудно. Страница с одним
# наброском даёт меньше страницы текста при том же свете.


@dataclass
class PhotoVerdict:
    ok: bool
    reason: str                  # что сказать пользователю
    line_height_px: float
    sharpness: float
    paper_fraction: float
    contrast: float

    def _line_height_text(self) -> str:
        if self.line_height_px == UNMEASURED_LINE_HEIGHT:
            return "не измерена — строк в профиле не видно"
        return f"{self.line_height_px:5.1f} px  (нужно ≥ {MIN_LINE_HEIGHT_PX})"

    def render(self) -> str:
        mark = "✅" if self.ok else "❌"
        return (
            f"{mark} {self.reason}\n"
            f"   высота строки : {self._line_height_text()}\n"
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


# Доля ширины листа, которую строка обязана закрасить, чтобы считаться
# строкой. Доля *кадра*, а не доля пикселей: порог по рангу уезжает вместе с
# тем, сколько чернил на странице, а этот — нет. 0.02 выбрана прогоном по
# страницам с известным шагом строк, от 28 px до 260.
_LINE_ROW_SHARE = 0.02
# Строка тоньше двух строк пикселей — это крапина, а не строка.
_MIN_BAND_PX = 2


def _ink_threshold(region: np.ndarray) -> float:
    """Граница между бумагой и чернилами — метод Оцу, по гистограмме.

    Порог по рангу («35-й перцентиль — это чернила») предполагает, что
    чернила занимают треть страницы. На настоящей странице их около 5%, так
    что порог садился на бумагу, маска захватывала весь лист, профиль
    выходил плоским — и функция отвечала «не измерено» почти всегда. Оцу
    ищет впадину между двумя горбами яркости и не знает заранее, какой из
    них больше.
    """
    hist = np.histogram(region, bins=256, range=(0, 256))[0]
    total = hist.sum()
    if total == 0:
        return 0.0
    weight = np.cumsum(hist)
    moment = np.cumsum(hist * np.arange(256))
    usable = (weight > 0) & (total - weight > 0)
    if not usable.any():
        return 0.0
    dark = weight[usable]
    light = total - dark
    between = dark * light * (moment[usable] / dark - (moment[-1] - moment[usable]) / light) ** 2
    return float(np.arange(256)[usable][int(np.argmax(between))])


def _ink_bands(active: np.ndarray) -> list[tuple[int, int]]:
    """Полосы подряд идущих строк с чернилами — по одной на строку текста."""
    found: list[tuple[int, int]] = []
    start: int | None = None
    for row, on in enumerate(active):
        if on and start is None:
            start = row
        elif not on and start is not None:
            found.append((start, row))
            start = None
    if start is not None:
        found.append((start, len(active)))
    return [band for band in found if band[1] - band[0] >= _MIN_BAND_PX]


def _line_height(region: np.ndarray) -> float:
    """Шаг между строками: медиана расстояний между полосами чернил.

    Раньше считалось иначе — высота листа, делённая на число найденных
    строк. Это меряет не строку, а страницу: один рисунок или пустое поле
    внизу растягивают ответ во столько раз, во сколько они велики, и на
    странице с рисунком среднее расходилось с медианой в 2.5-16 раз.
    Медиана расстояний между соседними полосами не знает ни про поля, ни про
    рисунок — она про то, как часто автор переносит руку на новую строку.

    Ушёл и минимум в три строки: страница, написанная крупно, несёт их
    меньше — и отбраковывалась как мелкий текст, ровно наоборот смыслу
    проверки. Одна полоса теперь отвечает своей высотой: это заведомо не
    больше шага, то есть оценка снизу, а проверка ищет как раз нижнюю
    границу.

    UNMEASURED_LINE_HEIGHT остаётся ответом на «полос нет вовсе» — пустая
    страница или кадр, где чернил не видно.
    """
    if region.size == 0:
        return UNMEASURED_LINE_HEIGHT
    ink = region <= _ink_threshold(region)
    per_row = ink.sum(axis=1)
    if per_row.max() == 0:
        return UNMEASURED_LINE_HEIGHT
    bands = _ink_bands(per_row > max(1.0, _LINE_ROW_SHARE * region.shape[1]))
    if not bands:
        return UNMEASURED_LINE_HEIGHT
    if len(bands) == 1:
        return float(bands[0][1] - bands[0][0])
    centres = np.array([(top + bottom) / 2 for top, bottom in bands])
    return float(np.median(np.diff(centres)))


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
    elif line_h != UNMEASURED_LINE_HEIGHT and line_h < MIN_LINE_HEIGHT_PX:
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
