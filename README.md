# VolgaAsk

RAG-помощник по нормативным документам Волгатеха: устав, приказы, правила приёма, положения. Отвечает на вопросы студентов и сотрудников, опираясь на исходные документы.

---

## Структура репозитория

```
VolgaAsk/
├── README.md
├── ROADMAP.md
├── docs/                 # документация проекта
└── AiService/            # RAG-модуль
    ├── src/              # пакет: конвертация, чанкинг, эмбеддинги, поиск
    ├── tests/            # pytest-тесты поиска по корпусу
    ├── data/             # исходные PDF, чанки, эмбеддинги, локальные модели
    ├── docker-compose.yml
    ├── pyproject.toml
    └── .venv/
```

---

### `docs/`

Документация: описание архитектуры.

---

### `AiService/`

#### `src/`

| Папка | За что отвечает |
|-------|-----------------|
| `configs/` | Пути, имена моделей, параметры БД |
| `processing/` | Конвертация, чанкинг, эмбеддинги, поиск |
| `database/` | ORM-модель, загрузка данных в pgvector |
| `utils/` | Вспомогательные утилиты |
| `scripts/` | Скрипты для запуска |

#### `tests/`

`test_search.py` проверяет, что нужные фрагменты документов попадают в top-5 по 20 контрольным вопросам; ожидаемые подстроки лежат в `tests/data/questions.json`.

#### `data/`

Исходные PDF (`raw/`), результаты обработки (`processed/`, `chunks/`, `embeddings/`) и локально скачанные модели (`models/`).

---

## Запуск

Все команды — из папки `AiService`.

```bash
# 1. PostgreSQL + pgvector
docker compose up -d

# 2. Установка пакета в editable-режиме (зависимости уже в .venv)
.venv/Scripts/python -m pip install -e . --no-deps

# 3. Обработка и индексация корпуса (если ещё не сделано)
.venv/Scripts/python -m scripts.index

# 4. Поиск
.venv/Scripts/python -m scripts.search "Кто избирает ректора?" --top-k 5

# 5. Тесты
.venv/Scripts/python -m pytest -v
```

На Linux/macOS путь к интерпретатору — `.venv/bin/python`.

Engine создаётся в `src/database/session.py` (`create_db_engine()`): адрес берётся из `DATABASE_URL`, подключение ограничено `CONNECT_TIMEOUT_SECONDS`. Если векторная БД выключена, `Retriever` открывает соединение до загрузки моделей и сразу падает с `OperationalError`, а не висит на неопределённый таймаут; `search.py` в этом случае печатает подсказку `docker compose up -d`.

Тесты не требуют установки пакета: путь `src` pytest добавляет сам (настройка `pythonpath` в `pyproject.toml`). Установка из шага 2 нужна, чтобы скрипты запускались как `python -m scripts.*`.
