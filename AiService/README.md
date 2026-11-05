### `AiService/`

#### `src/`

| Папка | За что отвечает |
|-------|-----------------|
| `configs/` | Пути, имена моделей, параметры БД |
| `processing/` | Конвертация, чанкинг, эмбеддинги, поиск, **генерация** |
| `database/` | ORM-модель, загрузка данных в pgvector |
| `utils/` | Вспомогательные утилиты |
| `scripts/` | Скрипты для запуска |

#### `tests/`

`test_search.py` проверяет, что нужные фрагменты документов попадают в top-5 по 20 контрольным вопросам; ожидаемые подстроки и вопросы лежат в `tests/data/questions.json`.

#### `data/`

Исходные PDF (`raw/`), результаты обработки (`chunks/`, `embeddings/`) и локально скачанные модели (`models/`).

## Запуск

```bash
# 1. Разбиение PDF на чанки
python -m src.scripts.chunk

# 2. Создание эмбеддингов для чанков
python -m src.scripts.embed

# 3. Вставка векторов в PostgreSQL
python -m src.scripts.index

# 4. PostgreSQL + pgvector
docker compose up -d

# 5. Скачивание LLM-модели 
docker exec -it ollama ollama pull qwen2.5:3b

# 6. Поиск
python -m src.scripts.search "Кто избирает ректора?" --top-k 5

# 7. Запуск тестов (запуск из папки tests/)
python -m pytest -v

# 8. Запуск скрипта с генерацией ответов
python -m src.scripts.generate --top-k 5
```