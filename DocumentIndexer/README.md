# DocumentIndexer

Воркер формирует поисковый индекс из PDF. Он скачивает документы из каталога, проверяет текст, запускает локальное OCR при необходимости и записывает фрагменты в PostgreSQL. RagService читает таблицу `chunks` и строит запросы той же моделью `deepvk/USER2-base`. Формат индекса включает векторы размерности 768.

## Запуск через Docker

Из корня VolgaAsk:

```powershell
docker compose build kb-init
docker compose up -d document-indexer
```

`kb-init` создаёт схему и регистрирует исходные PDF. Воркер использует тот же образ, PostgreSQL с pgvector и локальную Ollama. Образ можно собрать отдельно командой `docker build -t volgaask-document-indexer ./DocumentIndexer`.

## Локальное окружение Python

Из папки `DocumentIndexer`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install .
```

В VS Code выберите `DocumentIndexer/.venv/Scripts/python.exe` через **Python: Select Interpreter**. Для запуска воркера на хосте задайте `DATABASE_URL`, `KB_DSN`, `PGPASSWORD` и `OLLAMA_HOST`, затем выполните `python worker.py init` и `python worker.py` в этом окружении. Для сканов на хосте также нужны OCRmyPDF и русский Tesseract. В Docker они установлены в образе.
