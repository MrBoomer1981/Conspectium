# PLAN.md

План работ для Claude Code. Лежит в корне репозитория рядом с `CLAUDE.md`.

**Как работать с этим файлом:**

1. Пользователь называет номер задачи. Ты выполняешь **только её**.
2. Перед кодом опиши план изменений и дождись подтверждения.
3. Выполнил — поставь `[x]` в списке ниже и обнови раздел «Состояние»
   строго по шаблону.
4. Не делай ничего из следующих задач, даже если это «займёт две минуты».
5. Не добавляй абстракций, кэширования, очередей, ретраев там, где
   это не написано явно.
6. Нашёл в этом файле противоречие или недосказанность — **спроси**,
   не решай сам.
7. Спорный вопрос про типы, границы и семантику полей сначала ищи
   в разделе «Контракты» в конце файла.

---

## Прогресс

- [ ] 1. Каркас и деплой
- [ ] 2. Пользователи и события
- [ ] 3. Приём фотографии
- [ ] 4. Проверка кадра
- [ ] 5. Распознавание
- [ ] 6. Три прогона и сравнение
- [ ] 7. Проверка вычислений
- [ ] 8. Сохранение и лимиты
- [ ] 9. Word и альбомы
- [ ] 10. Надёжность

## Состояние

Обновляй строго по этому шаблону, ничего не добавляя и не убирая:

```
Выполнено: —
Текущая задача: 1
Следующая задача: 2
Блокеры: нет
```

---

## Целевая структура

```
app/
  __init__.py
  main.py
  bot/
    __init__.py
    handlers.py
    texts.py
    middlewares.py
    albums.py
  services/
    __init__.py
    vision.py
    images.py
    limits.py
    photoguard.py      # готовый, не менять
    consensus.py       # готовый, не менять
    mathcheck.py       # готовый, не менять
  db/
    __init__.py
    models.py
    session.py
    migrations/
  core/
    __init__.py
    config.py
    events.py
tests/
  __init__.py
CLAUDE.md
PLAN.md
prompts-v3.md
requirements.txt
requirements-dev.txt
Procfile
.env.example
```

**Все пути пишутся от корня репозитория.** `app` — пакет. Импорты
абсолютные и всегда с префиксом `app.`: `from app.core.config import
settings`. Относительных импортов не использовать.

`app/bot/albums.py` создаётся в задаче 9, раньше его нет.

### Готовые модули

`photoguard.py`, `consensus.py`, `mathcheck.py` уже написаны и покрыты
тестами. **Не переписывать, не «улучшать», не расширять.** Только
импортировать и вызывать. Нашёл в них ошибку — сообщи, не правь.

```python
# photoguard
check_photo_bytes(data: bytes) -> PhotoVerdict
#   PhotoVerdict: .ok, .reason, .line_height_px, .sharpness,
#                 .paper_fraction, .contrast

# consensus
compare(runs: list[str]) -> ConsensusReport       # .divergences, .agreement
compare_text(runs: list[str]) -> TextConsensus    # .similarity
pick_representative(runs: list[str]) -> int       # индекс лучшего прогона

# mathcheck
check(markdown: str) -> Report                    # .ok, .issues, .render()
#   Issue: .kind, .severity, .message, .detail, .suggestion
```

Во всех трёх `runs` — список строк `markdown`, не объекты.
Структура `Divergence` — в разделе «Контракты».

---

## Переменные окружения

```
BOT_TOKEN=                       обязательна
DATABASE_URL=                    обязательна
GEMINI_API_KEY=                  обязательна
WEBHOOK_URL=                     обязательна
WEBHOOK_SECRET=                  обязательна
AI_ENABLED=true
DAILY_PAGES_PER_USER=30
DAILY_COST_LIMIT_USD=5
VISION_RUNS=3
VISION_MODEL=gemini-2.5-flash-lite
MIN_MARKDOWN_LEN=40
MAX_ALBUM_PAGES=10
LOG_LEVEL=INFO
```

Пять обязательных переменных: без любой из них приложение **падает
на старте**, а не при первом запросе.

`WEBHOOK_URL` — **базовый адрес сервиса без пути**, например
`https://konspekt-bot.up.railway.app`. Путь приложение собирает само:
`{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}`. Не класть путь в переменную.

`VISION_RUNS` меньше 2 запрещён: сравнивать будет не с чем.
Валидировать в `Settings` и падать на старте.

**Все суточные границы — UTC.** И сброс `pages_used_today`, и выборка
`ai_calls` за сегодня.

## Зависимости

`requirements.txt` — прод:

```
fastapi
uvicorn[standard]
aiogram>=3.30
sqlalchemy[asyncio]>=2.0
asyncpg
alembic
pydantic-settings
google-genai
pillow
numpy
python-docx
```

`requirements-dev.txt` — только локально:

```
-r requirements.txt
pytest
pytest-asyncio
```

Импорт клиента Gemini: `from google import genai`.
Не добавляй ничего сверх этих списков без явного запроса.

---

## Транзакционная модель

**Читать до задачи 2.** Здесь ровно три правила, и они объясняют,
почему в проекте живут две разные сессии.

**1. Основная сессия — из мидлвари, одна на апдейт.** Мидлварь открывает
её, кладёт в `data["session"]`, коммитит после хендлера, откатывает при
исключении. В ней живёт всё: `notes`, `users`, `events`.

**2. `events` транзакционные и при откате теряются.** Это принято
сознательно: событие описывает то, чего в итоге не произошло, и хранить
его смысла нет. `session.begin_nested()` внутри `log_event` нужен
**не** для переживания отката, а для другого: если INSERT события упадёт,
без SAVEPOINT он отравит всю транзакцию, и «проглоченная» ошибка уронит
следующий же запрос.

**3. `ai_calls` пишутся в ОТДЕЛЬНОЙ сессии и коммитятся сразу.**
Деньги потрачены независимо от того, чем кончилась обработка. Строка
расходов обязана пережить откат основной транзакции, иначе дневной
потолок будет занижен и предохранитель перестанет работать.

⚠️ `session.begin_nested()` **этого не даёт**. SAVEPOINT живёт внутри
внешней транзакции и уходит вместе с ней при откате. Единственный
работающий способ — своя сессия со своим коммитом:

```python
async def log_ai_calls(user_id: int, stats: list[CallStats]) -> None:
    """Пишет ai_calls в собственной сессии и коммитит немедленно.
    Не принимает session: строки расходов не должны зависеть
    от судьбы основной транзакции."""
    async with async_session_maker() as own:
        async with own.begin():
            own.add_all([...])
```

Следствие: в базе могут оказаться `ai_calls` без соответствующей `Note`.
Это **правильно** — деньги были потрачены.

**`ai_calls` без `Note` — ожидаемый, а не аварийный результат.** Так
выглядит любая обработка, где Gemini вызывался, но запись не создалась:
`rejected`, `NO_TEXT_FOUND`, `transcribe_consensus` вернул `None`,
пропущенная страница альбома, необработанная ошибка после вызова модели.
Не пытайся «чинить» такие строки и не заводи для них компенсирующих
записей — финансовый учёт ведётся независимо от учёта записей.

**Исключение для `note_failed`.** Глобальный обработчик ошибок работает
тогда, когда основная транзакция уже откатывается. Событие `note_failed`
пишется **в отдельной сессии**, тем же способом, что и `ai_calls`.
Все остальные события — в основной.

---

## Итоговый порядок обработки фотографии

**Каноническая последовательность для одиночного фото.** Если по ходу
задачи возникает вопрос «до или после» — ответ здесь.

```
 0. media_group_id задан?                            ← в буфер, выход (задача 9)
 1. взять message.photo[-1]
 2. скачать в память
 3. сжать (images.compress)
 4. проверить лимиты (limits.check_limits, pages=1)   ← отказ: выход
 5. проверить кадр (photoguard.check_photo_bytes)     ← отказ: выход
 6. ответить texts.PROCESSING
 7. три прогона распознавания (vision.transcribe_consensus)
 8. записать расходы (vision.log_ai_calls)            ← всегда, своя сессия
 9. результат None                                    ← texts.ERROR_GENERIC, выход
10. verdict == "rejected"                             ← texts.REJECTED_QUALITY, выход
11. markdown короче MIN_MARKDOWN_LEN                  ← texts.NO_TEXT_FOUND, выход
12. проверить вычисления (mathcheck.check)
13. сохранить Note
14. списать квоту (limits.consume, pages=1)
15. записать событие note_processed
16. ответить пользователю
```

**Любой выход на шагах 4, 5, 9, 10, 11 означает одно и то же:** запись
не создаётся, квота не списывается, `note_processed` не пишется,
`note_failed` **тоже не пишется** (это штатные отказы, а не сбои),
пользователь получает ровно одно сообщение с причиной.

**Шаг 8 выполняется всегда**, если дошли до шага 7.

**Шаг 15 идёт строго между `consume` и ответом пользователю.** Событие
означает «обработка полностью завершилась успешно», поэтому оно не может
быть записано раньше, чем сохранены запись и квота.

Что отправляется на шаге 16:

1. `title` и `markdown` — основной текст записи
2. если `verdict == "needs_review"` — `texts.NEEDS_REVIEW`
3. если `mathcheck` что-то нашёл — `report.render()`
4. если `numeric_divergences` непусты — `texts.DIVERGENCES_HEADER`
   и список расхождений, по строке на элемент
5. если `uncertain` непуст — `texts.UNCERTAIN_HEADER` и список спорных
   мест, по строке: `«{text}» — {why}`

Пункты 2–5 идут **одним отдельным сообщением** после основного текста.

### Когда появляется сохранение

Шаги 13–15 реализуются **в задаче 8** (событие `note_processed` получает
полный контракт в задаче 10). До задачи 8, в задачах 5–7, результат
только отправляется пользователю: таблицы `notes` ещё нет. Не создавай
`Note` раньше задачи 8. Фразы «пометить запись» в задачах 6 и 7 означают
«выставить переменную `verdict` и показать пользователю».

### Почему такой порядок

**Лимиты раньше проверки кадра:** при `AI_ENABLED=false` или исчерпанном
потолке бессмысленно просить переснять фотографию.

**`PROCESSING` после проверки кадра:** до неё обработка занимает доли
секунды, и «обрабатываю» с мгновенным отказом выглядит глупо.

**Расходы отдельным шагом и отдельной сессией:** см. «Транзакционная
модель».

**Квота списывается после успешного сохранения.**

### Порядок появления шагов в коде

| Шаг | Появляется в задаче | Куда встраивается |
|---|---|---|
| 1–3 | 3 | с нуля |
| 5 | 4 | после шага 3 |
| 6 | 3 временно, в задаче 4 переезжает | после шага 5 |
| 7, 8, 9, 11 | 5 (один прогон), переписаны в 6 | после шага 6 |
| 10 | 6 | между шагами 9 и 11 |
| 12 | 7 | после шага 11 |
| 4 | 8 | **перед** шагом 5 из задачи 4 |
| 13–15 | 8 | после шага 12 |
| 0 | 9 | **в самое начало**, перед шагом 1 |

Задачи 8 и 9 вставляют свои шаги перед чужими. Это единственная
разрешённая правка чужого шага: **порядок вызовов менять можно,
логику внутри — нет.**

---

## Все тексты для пользователя

Живут в `app/bot/texts.py`, русский язык.

| Константа | Когда отправляется |
|---|---|
| `START` | команда `/start` |
| `PROCESSING` | шаг 6: кадр принят, начинается распознавание |
| `NO_TEXT_FOUND` | markdown короче `MIN_MARKDOWN_LEN` |
| `REJECTED_QUALITY` | `verdict == "rejected"`; для альбома — если не прошла ни одна страница |
| `NEEDS_REVIEW` | `verdict == "needs_review"` |
| `DIVERGENCES_HEADER` | заголовок списка числовых расхождений |
| `UNCERTAIN_HEADER` | заголовок списка спорных мест |
| `LIMIT_PAGES` | исчерпан суточный лимит страниц |
| `LIMIT_COST` | превышен дневной потолок расходов |
| `AI_DISABLED` | `AI_ENABLED=false` на AI-зависимом пути |
| `DOCX_ONLY` | документ не `.docx` |
| `FILE_TOO_BIG` | файл больше 5 МБ |
| `TOO_MANY_PAGES` | в альбоме больше `MAX_ALBUM_PAGES` страниц |
| `PAGE_SKIPPED` | страница альбома пропущена, шаблон с номером и причиной |
| `ERROR_GENERIC` | необработанная ошибка, а также `transcribe_consensus` вернул `None` |

**Единственное исключение:** `PhotoVerdict.reason` из `photoguard`
отдаётся пользователю как есть.

Никаких строк для пользователя вне `texts.py` — включая заголовки
списков и разделители.

---

# Задача 1. Каркас и деплой

## Создать

**`app/core/config.py`** — `Settings(BaseSettings)` со всеми переменными.
Экземпляр `settings` на уровне модуля. Валидация `VISION_RUNS >= 2`.
Константа тарифа:

```python
PRICE_PER_MTOK = {"gemini-2.5-flash-lite": (0.10, 0.40)}  # (вход, выход), USD
```

Модели нет в словаре → стоимость `None`, а не `KeyError`.

⚠️ **Нормализация `DATABASE_URL`.** Аддон Postgres на Railway выдаёт
строку вида `postgresql://…`, а SQLAlchemy с asyncpg требует
`postgresql+asyncpg://…`. Без приведения приложение упадёт на старте
с `InvalidRequestError`, и то же самое произойдёт в `alembic upgrade head`
при деплое.

В `Settings` — валидатор, который подменяет схему:

```python
@field_validator("DATABASE_URL")
@classmethod
def _asyncpg_scheme(cls, v: str) -> str:
    if v.startswith("postgres://"):
        v = v.replace("postgres://", "postgresql://", 1)
    if v.startswith("postgresql://"):
        v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
    return v
```

Переменную в Railway при этом **не трогать**: там она проставляется
аддоном автоматически и может обновиться при пересоздании базы.
Приводить схему только в коде.

**`app/db/session.py`** — асинхронный движок, `async_session_maker`
и зависимость `get_session()` для маршрутов FastAPI. Хендлеры aiogram
сессию получают иначе, см. задачу 2. Первый потребитель `get_session()`
появится в задаче 10 (`/health`) — это нормально, отдельного применения
сейчас не выдумывай.

`async_session_maker` дальше используется ещё и напрямую, для отдельных
сессий из «Транзакционной модели». Экспортируй его из модуля.

`env.py` Alembic берёт строку подключения **из `settings`**, а не из
`alembic.ini`: иначе нормализация схемы не применится и миграции
на деплое упадут. Сам каталог миграций — `app/db/migrations/`,
как в «Целевой структуре»; `script_location` в `alembic.ini` указывает
туда.

**Движок создаётся с `pool_pre_ping=True` и `pool_recycle=1800`.**
Это не ретрай и не отказоустойчивость, а обязательная настройка для
управляемого Postgres: провайдер закрывает простаивающие соединения,
а бот по своей природе простаивает часами между фотографиями. Без
`pool_pre_ping` первый же запрос после паузы упадёт на мёртвом
соединении из пула — и выглядеть это будет как случайная ошибка базы.

**`app/db/models.py`** — декларативная база и две модели:

```python
class User(Base):
    __tablename__ = "users"
    id: int                     # PK
    tg_id: int                  # BIGINT, unique, not null, index
    username: str | None
    first_name: str | None
    created_at: datetime        # server_default=now()
    pages_used_today: int       # not null, default 0
    quota_reset_at: date | None # сутки (UTC), за которые посчитан счётчик

class Event(Base):
    __tablename__ = "events"
    id: int                     # PK
    user_id: int | None         # FK users.id, index
    type: str                   # not null, index
    payload: dict               # JSONB, not null, default {}
    created_at: datetime        # server_default=now(), index
```

**`app/bot/texts.py`** — пока только `START`.

**`app/bot/handlers.py`** — роутер aiogram, `/start` отвечает `texts.START`.

**`app/main.py`** — приложение FastAPI:

- `Bot` и `Dispatcher` создаются **один раз на уровне модуля**,
  не в обработчике запроса
- жизненный цикл — через `lifespan` FastAPI, не через устаревшие
  `@app.on_event`
- на старте: `set_webhook` на `{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}`
  с `secret_token=WEBHOOK_SECRET`. **Ошибка `set_webhook` — падение
  приложения**, а не предупреждение в лог: бот без вебхука бесполезен
- `POST /webhook/{secret}` — сверяет `secret` из пути с
  `settings.WEBHOOK_SECRET` и заголовок `X-Telegram-Bot-Api-Secret-Token`;
  несовпадение любого → 403. Двойная проверка намеренна, не упрощать
- `GET /health` → `{"status": "ok"}`
- на остановке: `bot.session.close()`

**Alembic** — на асинхронный движок, миграция `001_users_events`.

**`Procfile`**:

```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Версия Python фиксируется явно.** Без этого Railway возьмёт свою
версию по умолчанию, и код может собраться не на том, на чём
проверялся локально. Файл `.python-version` в корне:

```
3.12
```

**`.env.example`** — все переменные из списка выше, обязательные
с пустым значением, остальные с дефолтами. Реальный `.env`
в репозиторий не коммитить: добавь его в `.gitignore` вместе
с `__pycache__/`, `*.pyc` и `.venv/`.

## Критерий приёмки

`/start` живому боту → ответ приходит **с задеплоенной на Railway версии**.
Не с локальной, не через polling.
`GET /health` на публичном URL отдаёт 200.

## Не делать

Никакой обработки фото. Никаких вызовов модели. Никакой бизнес-логики.

## Заметки

- aiogram 3.x: `Dispatcher.feed_update(bot, update)` для вебхука.
- Обработка апдейта идёт **внутри запроса вебхука**, ответ 200 уходит
  после её завершения. Осознанный выбор, см. «Известные риски».
  Не переделывать на фоновые задачи по своей инициативе.

---

# Задача 2. Пользователи и события

Прочитай раздел «Транзакционная модель» перед началом.

## Создать

**`app/core/events.py`**:

```python
async def log_event(
    session: AsyncSession,
    user_id: int | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    """Записать событие в ОСНОВНУЮ сессию. Транзакционное:
    при откате апдейта событие теряется, и это нормально.

    Никогда не бросает исключение наружу.
    Вставка внутри session.begin_nested() — SAVEPOINT нужен не для
    переживания отката, а чтобы упавший INSERT не отравил транзакцию
    целиком и «проглоченная» ошибка не уронила следующий запрос.

    Параметр называется event_type, а не type: встроенное имя
    затенять не надо. Колонка в базе остаётся type."""

async def log_event_standalone(
    user_id: int | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    """То же, но в собственной сессии с немедленным коммитом.
    Только для случаев, когда основная транзакция уже откатывается —
    то есть для note_failed из глобального обработчика ошибок
    (задача 10). Больше нигде не использовать."""
```

**`app/bot/middlewares.py`** — мидлварь aiogram, на каждый апдейт:
- открывает сессию, кладёт в `data["session"]`
- находит или создаёт пользователя по `tg_id`, кладёт в `data["user"]`
- при создании пишет событие `user_registered`
- коммитит после хендлера, откатывает при исключении

Зависимость `get_session()` из FastAPI в хендлерах aiogram не работает —
это разные механизмы.

**`handlers.py`** — `/start` получает `session` и `user` готовыми
из аргументов.

## Критерий приёмки

После `/start` в `users` одна строка, в `events` одна строка
`user_registered`. Второй `/start` дубля не создаёт и события не пишет.

## Не делать

Не строить систему аналитики. Не использовать `log_event_standalone`
нигде, кроме задачи 10.

---

# Задача 3. Приём фотографии

## Создать

**`app/services/images.py`**:

```python
def compress(image_bytes: bytes, max_side: int = 1500, quality: int = 85) -> bytes:
    """Ресайз по длинной стороне и перекодирование в JPEG.
    Учитывает EXIF-ориентацию (ImageOps.exif_transpose).
    Изображение меньше max_side не увеличивать."""
```

**Параметры `max_side=1500` и `quality=85` менять нельзя.** Пороги
`photoguard` откалиброваны на изображении именно после этого сжатия:
`line_height_px` и `sharpness` прямо зависят от разрешения.

**`handlers.py`** — хендлер `F.photo`, шаги 1–3:

1. `message.photo[-1]` — самая большая версия. Меньшие — превью Telegram.
2. Скачать в память через `bot.download`, на диск не писать.
3. Сжать.
4. Ответить `texts.PROCESSING` (временно: в задаче 4 переедет).
5. Событие `note_captured` с payload по контракту (см. «Контракты»).

**Оригинал не сохранять ни на диск, ни в базу.**

## Критерий приёмки

Фото уходит боту → приходит ответ. В `note_captured` видно сжатие,
обычно в 5–15 раз.

## Не делать

Не вызывать модель. Не сохранять запись. Про `media_group_id` пока
не думать — альбомы в задаче 9.

---

# Задача 4. Проверка кадра

## Сделать

Положить готовый `photoguard.py` в `app/services/`. Не менять.

Шаг 5 канонического порядка, **до любого обращения к модели**:

```python
photo_verdict = check_photo_bytes(compressed)
await log_event(session, user.id,
    "photo_accepted" if photo_verdict.ok else "photo_rejected",
    {
        "reason": photo_verdict.reason,
        "line_height_px": photo_verdict.line_height_px,
        "sharpness": photo_verdict.sharpness,
        "paper_fraction": photo_verdict.paper_fraction,
        "contrast": photo_verdict.contrast,
    })
if not photo_verdict.ok:
    await message.answer(photo_verdict.reason)
    return
```

Переменная называется `photo_verdict`, а не `verdict`: с задачи 6
в том же хендлере появится `verdict` — строка `clean | needs_review |
rejected`. Разные вещи, одинаковое имя рано или поздно перепутают.

`texts.PROCESSING` отправляется **после** этого блока.

Метрики пишутся **для всех** фотографий, включая принятые: это данные
для будущей калибровки порогов.

## Критерий приёмки

Фото издалека или в темноте → отказ с человеческой формулировкой,
в логах нет обращения к Gemini.

## Не делать

Не подбирать пороги. Значения в модуле — рабочая гипотеза.

---

# Задача 5. Распознавание

## Создать

**`app/services/vision.py`**. Типы данных:

```python
@dataclass
class Uncertain:
    text: str
    where: str
    why: str
    alternatives: list[str]

@dataclass
class Transcription:
    title: str
    subject: str | None
    markdown: str
    margin_notes: list[str]
    uncertain: list[Uncertain]
    numeric_tokens: list[str]
    unreadable_count: int

@dataclass
class CallStats:
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    latency_ms: int
    success: bool
    error: str | None
```

Семантика `success`, `latency_ms` и `cost_usd` — в разделе «Контракты».
Прочитай его перед реализацией.

Функции:

```python
async def transcribe(
    image_bytes: bytes,
) -> tuple[Transcription | None, list[CallStats]]:
    """Один вызов Gemini. В базу не ходит вообще.
    Возвращает разобранный результат и статистику каждой попытки:
    в этой задаче попытка всегда одна, в задаче 10 их станет до трёх.
    Первый элемент None при: сетевой ошибке, невалидном JSON,
    несоответствии схеме. Список статистики непуст всегда."""

async def log_ai_calls(user_id: int, stats: list[CallStats]) -> None:
    """Пишет строки в ai_calls в СОБСТВЕННОЙ сессии, с немедленным
    коммитом. Не принимает session — см. «Транзакционная модель».
    По одной строке на каждую попытку, успешную и неуспешную."""
```

**Почему ни `transcribe`, ни `transcribe_consensus` не принимают сессию.**
В задаче 6 прогоны идут через `asyncio.gather`, в задаче 9 через `gather`
идут ещё и страницы альбома. Одна `AsyncSession` конкурентного
использования не выдерживает — SQLAlchemy бросит
`IllegalStateChangeError`. Поэтому **всё, что вызывает модель, к базе
не обращается**, а статистику возвращает наверх.

### Вызов Gemini

Чтобы не выбирать наугад:

```python
client = genai.Client(api_key=settings.GEMINI_API_KEY)

response = await client.aio.models.generate_content(
    model=settings.VISION_MODEL,
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        TRANSCRIBE_PROMPT,
    ],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=1.0,
        max_output_tokens=8192,
    ),
)
```

- изображение приходит после `compress`, значит всегда `image/jpeg`
- `response_mime_type="application/json"` снимает обёртку ```json,
  но `parse_response` обязан пережить её появление всё равно
- **`temperature` не понижать.** Три прогона в задаче 6 работают
  ровно за счёт разброса между сэмплами. При температуре 0 прогоны
  станут одинаковыми, согласие всегда будет 100%, и защита от выдумок
  перестанет работать
- схему в `response_schema` не задавать: разбор и валидация делаются
  своим кодом, ему всё равно нужно переживать мусор
- таймаут ставится снаружи, через `asyncio.wait_for` — задача 10

Клиент создавать **один раз на уровне модуля**, не на каждый вызов.

Промпт — константа `TRANSCRIBE_PROMPT`, текст из `prompts-v3.md`
**дословно**. **Не удлинять**: каждое дополнительное правило ухудшает
основную задачу, это проверено экспериментально.

### Разбор ответа

Чистая функция без ввода-вывода:

```python
def parse_response(raw: str) -> Transcription | None:
    """Никогда не бросает исключение — возвращает None."""
```

Полная таблица типов и запасных значений — в разделе «Контракты».

### Учёт расходов

Модель `AiCall`, миграция `002_ai_calls`:

```python
class AiCall(Base):
    __tablename__ = "ai_calls"
    id: int
    user_id: int | None         # FK, index
    kind: str                   # "transcribe"
    model: str
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    latency_ms: int
    success: bool               # not null
    error: str | None
    created_at: datetime        # server_default=now(), index
```

Стоимость — по `settings.PRICE_PER_MTOK`, токены из `usage_metadata`;
если их нет — `None`, не выдумывать.

### Подключить к хендлеру

```
6.  отправить texts.PROCESSING
7.  result, stats = await transcribe(compressed)
8.  await log_ai_calls(user.id, stats)               # всегда
9.  result is None                          -> texts.ERROR_GENERIC, выход
11. markdown короче MIN_MARKDOWN_LEN        -> texts.NO_TEXT_FOUND, выход
    иначе отправить title и markdown
```

Шага 10 (вердикт) в этой задаче ещё нет, он появится в задаче 6.

Сообщение длиннее 4000 символов резать по границам абзацев —
у Telegram лимит 4096.

## Критерий приёмки

Фото конспекта → структурированный текст в ответе.
Фото без текста → `texts.NO_TEXT_FOUND`, не трейсбек.
Конспект на две страницы приходит целиком, не обрезается.
На одну фотографию ровно одна строка в `ai_calls`.

## Тесты обязательны

`tests/test_parse_response.py` — по одному тесту на каждую строку
таблицы разбора из «Контрактов», плюс:
- валидный JSON
- JSON в обёртке ```json … ```
- невалидный JSON
- пустая строка
- лишнее поле `confidence` → разбор проходит

Все случаи → `None` или корректный объект. Ни одного исключения.

## Не делать

Один вызов, без повторных попыток — они в задаче 10.
Без нескольких прогонов — это задача 6.
В базу пишутся только `ai_calls` и `events`.
Не оформлять вывод: ни разметки, ни кнопок, ни эмодзи.

---

# Задача 6. Три прогона и сравнение

## Сделать

Положить готовый `consensus.py` в `app/services/`. Не менять.

```python
@dataclass                          # не frozen: задача 7 меняет verdict
class TranscriptionResult:
    best: Transcription
    text_agreement: float          # 0..1
    numeric_divergences: list      # ConsensusReport.divergences
    verdict: str                   # "clean" | "needs_review" | "rejected"

async def transcribe_consensus(
    image_bytes: bytes,
) -> tuple[TranscriptionResult | None, list[CallStats]]:
    """settings.VISION_RUNS параллельных вызовов transcribe()
    через asyncio.gather(..., return_exceptions=True).

    В базу не ходит — статистику всех прогонов собирает в один плоский
    список и возвращает вторым элементом. Записывает её хендлер.

    Неудачные прогоны отбрасываются.
    Успешных меньше двух -> первый элемент None, но список статистики
    возвращается непустым всё равно."""
```

Как считать, дословно:

```python
markdowns = [t.markdown for t in ok_runs]
text_agreement = consensus.compare_text(markdowns).similarity
numeric_divergences = consensus.compare(markdowns).divergences
best = ok_runs[consensus.pick_representative(markdowns)]
```

Границы вердикта, непересекающиеся:

| `text_agreement` | verdict | Что делать |
|---|---|---|
| `>= 0.90` | `clean` | принять, показать числовые расхождения |
| `>= 0.70` и `< 0.90` | `needs_review` | принять, пометить всю запись |
| `< 0.70` | `rejected` | не сохранять, `texts.REJECTED_QUALITY` |

**Не склеивать куски разных прогонов.** Получится текст, которого
не выдавала ни одна модель, и проверка вычислений на нём потеряет смысл.

Числовые расхождения показываются при любом вердикте, кроме `rejected` —
это главный результат трёх прогонов. В задаче 8 они лягут в колонку
`Note.numeric_divergences`.

### Что меняется в хендлере

Вызов `transcribe` заменяется на `transcribe_consensus`. Вызов
`log_ai_calls` **остаётся в хендлере**, просто список статистики теперь
длиннее. Второго вызова `log_ai_calls` не появляется нигде.

```
7.  result, stats = await transcribe_consensus(compressed)
8.  await log_ai_calls(user.id, stats)               # всегда
9.  result is None                          -> texts.ERROR_GENERIC, выход
10. result.verdict == "rejected"            -> texts.REJECTED_QUALITY, выход
11. markdown короче MIN_MARKDOWN_LEN        -> texts.NO_TEXT_FOUND, выход
```

Проверка длины переезжает на `result.best.markdown` и делается **после**
вердикта, а не до.

`verdict` на этом этапе — обычная переменная. В базу пишутся только
`ai_calls` и `events`.

## Критерий приёмки

Чёткое фото одной страницы → `text_agreement` выше 0.9.
Разворот тетради издалека → `rejected`, запись не сохранена.
На одну фотографию ровно `VISION_RUNS` строк в `ai_calls`.

⚠️ Последний пункт действует **только до задачи 10**. После появления
повторных попыток число строк равно числу фактических вызовов Gemini
и может быть больше.

## Не делать

Не добавлять проверочный вызов модели «найди расхождения».
Экспериментально установлено: он выдумывает несуществующие расхождения
и не находит настоящие.

Не делать точечный переспрос по найденным расхождениям — это вторая
неделя.

Не переносить `log_ai_calls` внутрь `transcribe_consensus`.

Не понижать `temperature` ради «стабильности» — это сломает весь смысл
трёх прогонов.

---

# Задача 7. Проверка вычислений

## Сделать

Положить готовый `mathcheck.py` в `app/services/`. Не менять.

Шаг 12 — только если вердикт не `rejected` и текст не короче
`MIN_MARKDOWN_LEN`:

```python
report = mathcheck.check(result.best.markdown)
has_critical = any(i.severity == "critical" for i in report.issues)
if has_critical and result.verdict == "clean":
    result.verdict = "needs_review"
```

**Вердикт понижает только `severity == "critical"`.** Не `report.ok`:
он бывает `False` и на предупреждениях, а гнать человека перепроверять
всю запись из-за предупреждения — перебор. Остальные issues показываются,
но статус не меняют.

`clean` может стать `needs_review`. Обратного перехода нет.

**После этой задачи `result.verdict` считается финальным вердиктом
конвейера.** Именно он идёт в `Note.status` и в событие `note_processed`.

Показать найденное через `report.render()`. В базу пока ничего
не пишется: `report.issues` держится в переменной до задачи 8.

Событие `math_issues_found`: количество и список `kind`.

## Критерий приёмки

Страница с постоянной Планка `6,67·10⁻³⁴` → бот сообщает, что константа
записана неверно (табличное `6,626·10⁻³⁴`), и предлагает проверить.

## Не делать

Не просить модель проверять арифметику.

---

# Задача 8. Сохранение и лимиты

## Создать

Миграция `003_notes`:

```python
class Note(Base):
    __tablename__ = "notes"
    id: int
    user_id: int                # FK, index
    title: str                  # not null
    subject: str | None
    markdown: str               # TEXT
    source_type: str            # "photo" | "docx"
    page_count: int             # not null, default 1
    status: str                 # "ready" | "needs_review"
    uncertain: list             # JSONB, not null, default []
    issues: list                # JSONB, not null, default []
    numeric_divergences: list   # JSONB, not null, default []
    unreadable_count: int       # not null, default 0
    text_agreement: float | None
    photo_sharpness: float | None
    photo_line_height: float | None
    photo_paper_fraction: float | None
    photo_contrast: float | None
    created_at: datetime        # server_default=now(), index
```

`page_count` = **число страниц, реально вошедших в запись**, а не число
присланных. Для одиночного фото всегда 1.

**Сериализация обязательна.** `Uncertain` и `Issue` — dataclass'ы,
JSONB их не примет. Класть `[asdict(x) for x in ...]`. Структура
элемента `numeric_divergences` — в «Контрактах».

Откуда берутся значения для одиночного фото:

| Колонка | Источник |
|---|---|
| `title`, `subject`, `markdown` | `result.best` |
| `uncertain`, `unreadable_count` | `result.best` |
| `text_agreement`, `numeric_divergences` | `result` |
| `issues` | `report.issues` из задачи 7 |
| `photo_*` | `photo_verdict` из задачи 4 |
| `source_type` | `"photo"` |
| `page_count` | `1` |

Соответствие вердикта и статуса:

| verdict | Note.status |
|---|---|
| `clean` | `ready` |
| `needs_review` | `needs_review` |
| `rejected` | запись не создаётся вовсе |

После сохранения и `consume` — событие `note_processed` (шаг 15).
Полный контракт события — в задаче 10 и в «Контрактах»; здесь достаточно
записать его с теми полями, которые уже есть.

**`app/services/limits.py`**:

```python
async def check_limits(
    session: AsyncSession, user: User, pages: int
) -> str | None:
    """Вернуть текст отказа из texts.py, если нельзя, иначе None.
    Порядок проверок:
      1. settings.AI_ENABLED выключен          -> texts.AI_DISABLED
      2. сумма cost_usd в ai_calls за сегодня
         >= DAILY_COST_LIMIT_USD               -> texts.LIMIT_COST
      3. user.pages_used_today + pages
         > DAILY_PAGES_PER_USER                -> texts.LIMIT_PAGES

    Перед третьей проверкой: если user.quota_reset_at пуст ИЛИ меньше
    сегодняшней даты (UTC), обнулить pages_used_today и выставить
    quota_reset_at на сегодня. Пустой quota_reset_at — это каждый новый
    пользователь, и сравнение None с датой упадёт с TypeError.

    Строки ai_calls с cost_usd = None в сумму не входят."""

async def consume(session: AsyncSession, user: User, pages: int) -> None:
    """Увеличить pages_used_today. Вызывается ТОЛЬКО после успешного
    сохранения записи — шаг 14."""
```

**`DAILY_COST_LIMIT_USD` — мягкий лимит.** Проверяется только перед
началом обработки, бюджет под текущую операцию не резервируется.
Значит потолок может быть превышен на стоимость одного альбома.
Это принято сознательно: резервирование требует двухфазного учёта,
что на одном пользователе не окупается.

`check_limits` — шаг 4, **до** проверки кадра и до обращения к модели.
Вставить перед блоком из задачи 4.

`limits.py` импортирует `from app.bot import texts` и возвращает готовую
строку. Цикла импортов не возникает. Не заводи коды ошибок и словарь
соответствий.

Сутки везде по UTC.

## Критерий приёмки

31-я страница за сутки → `texts.LIMIT_PAGES`.
`AI_ENABLED=false` → `texts.AI_DISABLED`, ноль вызовов API.
Отклонённый по качеству кадр квоту не расходует.
Первое в жизни фото нового пользователя (`quota_reset_at is None`)
обрабатывается без ошибки.

## Тесты обязательны

`tests/test_limits.py`: под лимитом, ровно на лимите, над лимитом,
`quota_reset_at is None`, сброс на следующий день, выключенный
`AI_ENABLED`, превышенный потолок расходов, `ai_calls` с `cost_usd=None`
в выборке.

## Не делать

Лимиты одинаковые для всех, без настройки на пользователя и без тарифов.
Никаких команд `/limits` и `/stats` — смотри в базу напрямую.
Не делать фоновую задачу сброса счётчика: он сбрасывается лениво.
Не вводить блокировку строки пользователя — см. «Известные риски».

---

# Задача 9. Word и альбомы

## Сделать

### Документы `.docx`

Хендлер `F.document`:

- расширение не `.docx` → `texts.DOCX_ONLY`
- размер больше 5 МБ → `texts.FILE_TOO_BIG`
- текст извлекать через `python-docx`
- **модель не вызывать вообще.** В `.docx` текст уже машинный:
  распознавать нечего, структура есть. Заголовки Word → заголовки
  markdown, абзацы → абзацы. Это чистый код
- **`check_limits` не вызывается, `consume` не вызывается.** Денег
  не тратится, модель не дёргается; при `AI_ENABLED=false` Word
  обрабатывается как обычно
- `source_type = "docx"`, `page_count = 1`, `status = "ready"`,
  `text_agreement = None`, `numeric_divergences = []`, `issues = []`,
  `uncertain = []`, `unreadable_count = 0`, `photo_*` = `None`
- шаги 0, 4–10 и 12 пропускаются
- шаг 11 остаётся: пустой документ → `texts.NO_TEXT_FOUND`,
  запись не создаётся
- события `note_captured` и `note_processed` — по контракту для `docx`
  (см. «Контракты»)

### Альбомы

Telegram присылает альбом отдельными сообщениями с общим `media_group_id`.

**Ветвление в самом начале хендлера `F.photo`** — шаг 0, сразу после
сжатия и **до** проверки лимитов:

```python
if message.media_group_id:
    albums.add_page(message.media_group_id, PageInput(
        data=compressed,
        message_id=message.message_id,
        chat_id=message.chat.id,
        media_group_id=message.media_group_id,
        bytes_before=len(original),
        bytes_after=len(compressed),
        width=w, height=h,
    ))
    return          # шаги 4-16 для отдельной страницы НЕ выполняются
```

Одиночный конвейер к страницам альбома не применяется ни в какой части.
Метрики сжатия кладутся в буфер сразу: сессия этого апдейта скоро
закроется, а `note_captured` для страниц пишется позже, при разборе пачки.

**`app/bot/albums.py`** — буфер и сборка:

- словарь в памяти процесса: `media_group_id -> list[PageInput]`
- ждать 1.0 секунды после последнего сообщения группы

⚠️ **Единственный владелец пачки.** Несколько хендлеров могут дождаться
тишины одновременно. После ожидания хендлер **атомарно извлекает группу
из буфера** — `pop`. Продолжает обработку только тот, кому `pop` вернул
непустой список; остальные молча завершаются, ничего не отвечая
пользователю.

Без этого одна пачка обрабатывается дважды: двойные вызовы Gemini,
две записи, двойное списание квоты. Redis, очередь и любое внешнее
хранилище для этого не добавлять — `dict.pop` в однопроцессном
приложении атомарен и достаточен.

**Порядок страниц.** Перед обработкой пачка сортируется по `message_id`
по возрастанию. Порядковый номер `page` назначается **после сортировки**,
начиная с 1. Этот номер используется везде: в `PAGE_SKIPPED`,
в `note_captured`, в полях `page` у `numeric_divergences`, `uncertain`
и `issues`, и при склейке markdown. Порядок прихода апдейтов нумерацию
не определяет.

**Порядок проверок для пачки — строго такой:**

```
1. len(pages) > MAX_ALBUM_PAGES   -> texts.TOO_MANY_PAGES, выход
2. check_limits(pages=len(pages)) -> отказ: выход
3. по одному note_captured на страницу
4. ответить texts.PROCESSING (один раз, до gather)
5. gather по страницам
6. log_ai_calls один раз, на объединённой статистике
7. сборка записи, сохранение, consume, note_processed
```

Размер проверяется **раньше** лимитов: это форма запроса, а не расход.
Альбом из 11 страниц получает `TOO_MANY_PAGES` даже при исчерпанной
квоте.

**Обработка страниц:**

- параллельно через `asyncio.gather(..., return_exceptions=True)`
- для каждой: `check_photo_bytes`, затем `transcribe_consensus`
- ⚠️ **`log_ai_calls` вызывается один раз, после `gather`**, на
  объединённой статистике всех страниц. Не внутри обработки страницы

**Единая семантика отказа страницы.** Страница пропускается, если
случилось **любое** из:

| Причина | Что в `PAGE_SKIPPED` |
|---|---|
| кадр не прошёл `photoguard` | `photo_verdict.reason` |
| `transcribe_consensus` вернул `None` | «не удалось распознать» |
| `verdict == "rejected"` | «распознавание разошлось» |
| markdown короче `MIN_MARKDOWN_LEN` | «текста не найдено» |
| таймаут, исключение, любая другая ошибка | «ошибка обработки» |

**Ошибка одной страницы не отменяет обработку остальных.** Именно
поэтому `gather` вызывается с `return_exceptions=True`: исключение
превращается в `PAGE_SKIPPED`, а пачка обрабатывается дальше. Если же
сработал общий таймаут альбома и результаты остальных страниц получить
невозможно, `log_ai_calls` получает всю статистику, которую удалось
собрать до отмены.

Пропущенная страница: не входит в `page_count`, не входит в агрегаты,
квоту не расходует, `Note` из-за неё не отменяется, `note_failed`
не пишется. В ответ идёт `texts.PAGE_SKIPPED` с номером страницы
и причиной.

Не прошла **ни одна** страница → `texts.REJECTED_QUALITY`, запись
не создаётся, квота не списывается.

**Поля записи для альбома** — только по успешно обработанным страницам:

- `text_agreement` = минимум по обработанным страницам. Если обработана
  одна — её собственное значение, без поправок
- каждое `photo_*` = минимум по обработанным страницам
- `status` = `needs_review`, если хоть одна обработанная страница дала
  `needs_review`; иначе `ready`. Пропущенные страницы в расчёте
  не участвуют
- `uncertain`, `issues`, `numeric_divergences` — конкатенация, у каждого
  элемента добавлено поле `page`
- `unreadable_count` = сумма по обработанным страницам
- `markdown` — склейка через `\n\n---\n\n`, в порядке `page`
- `page_count` = число успешно обработанных страниц
- `consume(pages=page_count)` — за реально обработанные, не за присланные

**Потолок параллелизма.** В `vision.py` модульный
`asyncio.Semaphore(10)`, внутри которого делается каждый вызов Gemini.
Без него альбом даёт 30 одновременных запросов (с ретраями задачи 10 —
до 90), Gemini отвечает 429, ретраи их размножают. Три строки кода,
не очередь; ничего сверх семафора не добавлять.

## Критерий приёмки

Три фото одним альбомом → одна запись из трёх страниц, не три записи.
Пользователь получает один `PROCESSING`, а не три.
Альбом, где вторая страница смазана → запись из двух страниц,
в ответе сказано, что страница 2 пропущена, квота списана на 2.
Альбом из 11 страниц при исчерпанной квоте → `TOO_MANY_PAGES`,
не `LIMIT_PAGES`.
`.docx` сохраняется без единого вызова модели и при `AI_ENABLED=false`.

## Не делать

Никаких других форматов: ни PDF, ни `.doc`, ни `.txt`, ни фото,
присланных документом. Всё это — вежливый отказ.
Не извлекать из `.docx` картинки и таблицы: только текст и заголовки.
Буфер альбомов не выносить в Redis и не делать переживающим перезапуск.

---

# Задача 10. Надёжность

## Сделать

**Повторные попытки** внутри `transcribe()`: до трёх попыток, паузы
между ними 1 и 2 секунды (три попытки — две паузы).

**Цикл прерывается сразу после первой успешной попытки.** Оставшиеся
не выполняются.

Классификация ошибок — полная, чтобы не выбирать наугад:

| Повторять | Не повторять |
|---|---|
| таймаут `asyncio.wait_for` | 400, 401, 403, 404 |
| разрыв соединения, сброс, DNS | любая ошибка разбора или схемы |
| 408, 429 | пустой ответ модели |
| любой 5xx | |
| ошибка SDK без HTTP-кода | |

Правило на случай неизвестной ошибки: **если непонятно, транспортная
она или логическая — не повторять.** Лишний вызов стоит денег,
лишний отказ стоит одной кнопки «попробовать ещё раз».

⚠️ Ретраи умножаются на прогоны: 3 прогона × 3 попытки = до 9 вызовов
на страницу. Поэтому:
- ретраи только внутри `transcribe()`, **не** вокруг
  `transcribe_consensus()`
- каждая попытка возвращается в списке `CallStats` и доезжает
  до `log_ai_calls`
- семафор из задачи 9 общий на все попытки всех прогонов

**Таймауты:**

| Что | Сколько | Почему столько |
|---|---|---|
| один вызов модели | 30 с | штатный ответ ~6 с |
| `transcribe_consensus` | 120 с | 3 попытки × 30 с + паузы 1 и 2 с = 93 с, плюс запас |
| альбом целиком | 300 с | покрывает худший случай на 10 страницах |

Таймаут на консенсус обязан быть больше худшего случая одного прогона
с ретраями, иначе он срежет обработку раньше собственных попыток.

Таймаут альбома обязан покрывать худшее расписание страниц при
`Semaphore(10)`: для 10 страниц по 3 прогона это три волны по до 93
секунд каждая, то есть до 279 секунд. **300 секунд — нормативное
значение, а не приблизительная оценка**, и уменьшать его нельзя.

**Глобальный обработчик ошибок aiogram**: любое необработанное
исключение → пользователю `texts.ERROR_GENERIC`, подробности в лог
с трассировкой. **Ни одного трейсбека пользователю.**

Событие `note_failed` пишется **через `log_event_standalone`**:
основная транзакция в этот момент уже откатывается, и обычный
`log_event` пропадёт вместе с ней.

**События** `note_processed` и `note_failed` — по контракту
(см. «Контракты»).

**`GET /health`** дополнить проверкой соединения с базой:
при недоступной БД отдавать 503.

## Критерий приёмки

Подменить `GEMINI_API_KEY` на неверный → бот извиняется понятным текстом,
не молчит и не падает. В логах видна настоящая причина.
Строки в `ai_calls` появляются и при полностью неудачной обработке.
Событие `note_failed` есть в базе после необработанного исключения.

## Не делать

Не подключать Sentry и внешний мониторинг: логов Railway достаточно.
Не строить размыкатель цепи, не вводить экспоненциальный джиттер —
три попытки с фиксированными паузами закрывают всё, что бывает
на одном пользователе.
Не переписывать код предыдущих задач под предлогом надёжности.

---

# Контракты

Здесь собрано всё, что иначе пришлось бы додумывать. **При любом споре
о типах, границах и семантике — ответ отсюда.**

## `CallStats.success`

`success = True` **только если попытка дала пригодный `Transcription`**:
API ответил, JSON разобран, схема сошлась.

| Ситуация | `success` | `cost_usd` | Повторять |
|---|---|---|---|
| API 200, разбор прошёл | `True` | заполнен | нет, цикл кончается |
| API 200, невалидный JSON | `False` | **заполнен** | нет |
| API 200, схема не сошлась | `False` | **заполнен** | нет |
| API 429 / 5xx / таймаут | `False` | `None` | да |
| API 400 / 401 / 403 | `False` | `None` | нет |

Ключевое: **стоимость записывается всегда, когда модель ответила** —
токены сожжены независимо от того, поняли мы ответ или нет.

Одна попытка = один сетевой вызов Gemini со всем последующим разбором.

## `latency_ms`

Измеряется **одним монотонным таймером** (`time.monotonic()`) на нужном
интервале. **Не складывать `CallStats.latency_ms` между собой:** при
параллельном выполнении сумма не равна реальному времени.

| Где | Интервал |
|---|---|
| `CallStats` | одна попытка: от начала сетевого вызова до конца разбора её ответа |
| `note_processed`, фото | шаг 7 → конец шага 15 |
| `note_processed`, альбом | начало `gather` → конец сохранения и `consume` |
| `note_processed`, `.docx` | извлечение текста |

## `cost_usd`

- складываются только значения, отличные от `None`
- если **все** слагаемые `None` — итог `None`, не ноль
- если хоть одно известно — итог равен сумме известных
- для `.docx` — всегда `None`, вызовов не было
- для альбома — сумма по всем фактическим вызовам, включая повторные
  попытки и неуспешные прогоны

## `numeric_divergences`

`ConsensusReport.divergences` — список объектов `Divergence`:

```python
position: int                # порядковый номер числовой позиции
variants: dict[str, int]     # значение -> сколько прогонов за него
context: str                 # исходный текст числа
```

В JSONB кладётся `asdict`. Для альбома к каждому элементу добавляется
`page: int` — порядковый номер страницы после сортировки, с 1.

## Пустой markdown

Проверка длины делается **после `.strip()`**:

```python
len(markdown.strip()) < settings.MIN_MARKDOWN_LEN
```

Строка из пробелов и переводов строк считается пустой. Правило одно
для одиночного фото, страниц альбома и `.docx`.

## `parse_response`: типы полей

Неверный тип не роняет разбор — применяется запасное значение.

| Поле | Ожидается | Не тот тип или нет поля |
|---|---|---|
| `markdown` | непустая строка | → **`None` для всей записи** |
| `title` | строка | первые 60 символов первой непустой строки `markdown`; если и там пусто — `"Без заголовка"` |
| `subject` | строка | `None` |
| `margin_notes` | список строк | `[]`; элементы не-строки выбрасываются |
| `numeric_tokens` | список строк | `[]`; элементы не-строки выбрасываются |
| `unreadable_count` | целое | `0`; строку с числом привести, иначе `0` |
| `uncertain` | список объектов | `[]` |
| `uncertain[].text` | строка | **элемент пропускается** |
| `uncertain[].where` | строка | `""` |
| `uncertain[].why` | строка | `""` |
| `uncertain[].alternatives` | список строк | `[]` |

Обязательный ключ у элемента `uncertain` ровно один — `text`. Элемент
без него пропускается молча, весь ответ не отбрасывается.

Лишние поля игнорируются. Промпт v3 возвращает `confidence` — мы его
не используем сознательно: самооценка модели оказалась бесполезным
сигналом.

## `PageInput`

Поля буфера альбома: `data`, `message_id`, `chat_id`, `media_group_id`,
`bytes_before`, `bytes_after`, `width`, `height`.

`media_group_id` хранится в каждой странице и используется при
формировании `note_captured`. У всех страниц одной пачки он одинаковый.

## Событие `note_captured`

| Источник | payload |
|---|---|
| фото | `bytes_before`, `bytes_after`, `width`, `height`, `source_type: "photo"` |
| страница альбома | то же + `page`, `media_group_id`; пишется при разборе пачки, не при приёме |
| `.docx` | `bytes_before`, `source_type: "docx"` |

Для `.docx` полей `bytes_after`, `width` и `height` нет, потому что
документ не проходит сжатие изображения. Не подставлять для них
искусственные значения.

## Событие `note_processed`

Пишется **один раз, после успешного выполнения шагов 13 и 14** — то есть
после сохранения `Note` и успешного `consume`, но **до** отправки
финального ответа пользователю. Событие означает, что обработка записи
полностью завершилась.

Оно транзакционное: коммитится вместе с `Note` и изменением квоты
основной сессией. При любом штатном отказе (шаги 4, 5, 9, 10, 11)
не пишется.

| Поле | фото | альбом | `.docx` |
|---|---|---|---|
| `verdict` | финальный после задачи 7 | см. ниже | `"clean"` |
| `latency_ms` | шаги 7→15 | `gather`→сохранение | извлечение текста |
| `cost_usd` | сумма попыток | сумма по всем страницам | `None` |
| `page_count` | `1` | обработанных страниц | `1` |
| `source_type` | `"photo"` | `"photo"` | `"docx"` |
| `pages_skipped` | — | число пропущенных | — |

**`verdict` для альбома** считается только по успешно обработанным
страницам: если хотя бы одна из них дала `needs_review`, итог —
`needs_review`; иначе `clean`. Страницы, пропущенные из-за `photoguard`,
`transcribe_consensus == None`, `rejected`, короткого markdown или
ошибки обработки, в расчёте не участвуют.

## Событие `note_failed`

Пишется **только при необработанном исключении**, из глобального
обработчика, через `log_event_standalone`.

Штатные отказы — лимит, `AI_DISABLED`, плохой кадр, `rejected`,
`NO_TEXT_FOUND`, пропуск страницы альбома — **это не `note_failed`**.
Они уже отражены в своих событиях и в ответе пользователю.

payload: `{"reason": <тип исключения>, "where": <имя хендлера>}`.

## Границы тестирования

Обязательны тесты из задач 5 и 8, плюс ровно три интеграционных теста
на механизмы, где ошибка стоит настоящих денег:

1. **Повторная попытка.** `429`, затем успех → два элемента `CallStats`
   и две строки в `ai_calls`.
2. **Владелец пачки.** Два одновременных хендлера с одним
   `media_group_id` обрабатывают её ровно один раз.
3. **Независимость расходов.** Откат основной транзакции не удаляет
   уже закоммиченные `ai_calls`.

Больше ничего: ни на консенсус, ни на сборку альбома, ни на мидлварь,
ни на вебхук. Это осознанное ограничение объёма первой недели.

---

# Известные риски

Найдены, обсуждены, оставлены как есть. **Не чинить по своей
инициативе** — если один выстрелит, будет отдельная задача.

**Обработка идёт внутри запроса вебхука.** `POST /webhook` отвечает
Telegram 200 только после завершения `feed_update`, а это до 120 секунд
на фото и до 300 на альбом. Telegram считает апдейт недоставленным
примерно через минуту и присылает его снова — получится вторая обработка
того же фото: лишние вызовы Gemini и повторное списание квоты.
Признак: две одинаковые записи в `notes` с разницей в минуту и удвоенный
`ai_calls`. Лечится дедупликацией по `update_id` или ответом 200
до обработки — отдельной задачей и по решению пользователя.

⚠️ **Для альбомов этот риск усилен.** Атомарный `pop` защищает от двух
хендлеров внутри одной доставки, но повторно доставленные страницы
приходят как новые сообщения и соберутся в новую пачку под тем же
`media_group_id` — которую первый обработчик уже забрал. Альбом,
идущий 300 секунд, будет переслан Telegram гарантированно. Признак тот
же: удвоенные записи и расходы. Принято сознательно на время первой
недели.

**Гонка в проверке и списании квоты.** `check_limits` читает
`pages_used_today`, `consume` его увеличивает, между ними — секунды
работы с моделью. Две параллельные обработки одного пользователя могут
обе пройти проверку и обе списать квоту. Блокировка строки не вводится
сознательно: на одном пользователе цена ошибки — одна лишняя посчитанная
страница.

**Лимит расходов мягкий.** `DAILY_COST_LIMIT_USD` проверяется только
перед началом обработки, бюджет не резервируется. Потолок может быть
превышен на стоимость одного альбома — при текущих ценах это центы.

**Буфер альбомов живёт в памяти процесса.** Railway перезапускает
контейнер — недособранная пачка теряется молча. Redis на одного
пользователя не окупается.

---

# Определение готовности недели

- [ ] `/start` отвечает с задеплоенной версии
- [ ] Фото → структурированный текст
- [ ] Плохой кадр отклоняется до вызова модели
- [ ] Три прогона сравниваются, числовые расхождения показаны
- [ ] Ошибки в вычислениях находятся и показываются
- [ ] Лимиты работают; `AI_ENABLED=false` блокирует AI-зависимые пути,
      `.docx` продолжает обрабатываться без Gemini
- [ ] Альбом даёт одну запись и один `PROCESSING`
- [ ] Собранной пачкой владеет ровно один хендлер
- [ ] Таймаут альбома — 300 секунд
- [ ] `ai_calls` переживают откат основной транзакции
- [ ] `note_processed` пишется только после `Note` и `consume`
- [ ] Ни одного трейсбека пользователю
- [ ] События пишутся с первого дня
- [ ] Метрики кадров сохраняются для калибровки

---

# Бэклог. Не реализовывать и не предлагать

- Mini App и любой интерфейс кроме бота
- Карточки, интервальное повторение
- Поиск по записям
- Редактирование записи
- Точечный переспрос модели по найденным расхождениям
- Видео, расшифровка лекций
- Платежи, подписки
- Экспорт в любые форматы
- Оформление и дизайн ответов
- Кэширование, очереди, воркеры, Redis
- Дедупликация по `update_id`
- Блокировки строк, двухфазный учёт расходов
- Docker, CI, автотесты сверх перечисленных
