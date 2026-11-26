import hashlib
import logging
import os
import sys
from pathlib import Path
from datetime import date
from uuid import uuid5, NAMESPACE_URL

import psycopg
from sqlalchemy import delete, insert, text

from indexer import Indexer
from chunk_model import Chunk
from db import DEFAULT_KB_DSN, create_db_engine
from pipeline import DocumentFailure, index_chunks, prepare_pdf
from portal import fetch_pdf

ROOT = Path(os.getenv("KB_ROOT", Path(__file__).resolve().parent.parent / "storage" / "kb"))
KB_DSN = os.getenv("KB_DSN", DEFAULT_KB_DSN)
ENGINE = create_db_engine()
TITLES = {
    "141001_prikaz_380_p_pravila_vnutr_raspor": "Правила внутреннего распорядка обучающихся",
    "190125-ustav": "Устав ПГТУ",
    "241220-ustav-2024": "Изменения в устав ПГТУ (2024)",
    "cmk-pi-3-06-01-2017": "Положение о системе РИТМ",
    "pravila_priema_bs_v4_2026": "Правила приёма на бакалавриат и специалитет (2026)",
}


def paths(key):
    """Возвращает временный и опубликованный пути."""
    return ROOT / "staging" / f"{key}.pdf", ROOT / "raw" / f"{key}.pdf"


def seed(db, source):
    """Привязывает исходный PDF к существующим фрагментам или ставит в очередь."""
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    added = db.execute(text("""INSERT INTO kb_seeds VALUES (:hash) ON CONFLICT DO NOTHING
        RETURNING checksum"""), {"hash": digest}).first()
    if not added:
        return
    key = uuid5(NAMESPACE_URL, digest)
    stage, raw = paths(key)
    migrated = db.execute(text("""UPDATE chunks SET document_id=:key WHERE document_id=:old
        RETURNING document_date"""), {"key": str(key), "old": source.stem}).scalars().all()
    if migrated:
        stage.write_bytes(data)
        stage.replace(raw)
    title = TITLES.get(source.stem, "Изменения в устав ПГТУ (" + source.stem[-4:] + ")")
    try:
        existing_date = date.fromisoformat(migrated[0]) if migrated and migrated[0] else None
    except ValueError:
        existing_date = None
    db.execute(text("""INSERT INTO kb_documents(id,title,filename,document_date,checksum,status,payload)
        VALUES (:id,:title,:filename,:date,:checksum,:status,:payload)"""),
        dict(id=key, title=title, filename=source.name, date=existing_date, checksum=digest,
             status="ready" if migrated else "queued", payload=None if migrated else data))


def initialize():
    """Создаёт очередь и импортирует исходный корпус один раз."""
    for directory in paths("example"):
        directory.parent.mkdir(parents=True, exist_ok=True)
    Indexer(ENGINE).ensure_schema()
    with psycopg.connect(KB_DSN) as connection:
        connection.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
    for source in sorted((ROOT / "bootstrap").glob("*.pdf")):
        with ENGINE.begin() as db:
            seed(db, source)


def publish(db, row, stage, raw):
    """Готовит файл и публикует индекс в текущей транзакции."""
    if row.payload is None:
        try:
            with stage.open("wb") as stream:
                checksum = fetch_pdf(row.source, stream)
        except Exception as exc:
            raise DocumentFailure("download_failed") from exc
        if checksum != row.checksum:
            raise DocumentFailure("portal_changed")
    else:
        stage.write_bytes(row.payload)
    with stage.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise DocumentFailure("invalid_pdf")
    with prepare_pdf(stage) as (searchable, ocr_applied):
        for chunk in index_chunks(searchable, row.id, row.document_date):
            db.execute(insert(Chunk).values(**chunk))
    stage.replace(raw)
    db.execute(text("""UPDATE kb_documents SET status='ready',payload=NULL,ocr_applied=:ocr
        WHERE id=:id"""), {"id": row.id, "ocr": ocr_applied})


def process_one():
    """Берёт свободное задание и атомарно фиксирует результат."""
    with ENGINE.begin() as db:
        job = db.execute(text("""SELECT id,status FROM kb_documents
            WHERE status IN ('queued','indexing','deleting')
            ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1""")).first()
        if not job:
            return False
        if job.status == "queued":
            db.execute(text("UPDATE kb_documents SET status='indexing' WHERE id=:id"), {"id": job.id})
    with ENGINE.begin() as db:
        row = db.execute(text("""SELECT * FROM kb_documents WHERE id=:id
            AND status IN ('indexing','deleting') FOR UPDATE SKIP LOCKED"""), {"id": job.id}).first()
        if not row:
            return False
        stage, raw = paths(row.id)
        if row.status == "deleting":
            db.execute(delete(Chunk).where(Chunk.document_id == str(row.id)))
            raw.unlink(missing_ok=True)
            db.execute(text("DELETE FROM kb_documents WHERE id=:id"), {"id": row.id})
            return True
        try:
            with db.begin_nested():
                publish(db, row, stage, raw)
        except Exception as exc:
            logging.exception("Не удалось опубликовать %s", row.id)
            raw.unlink(missing_ok=True)
            code = str(exc) if isinstance(exc, DocumentFailure) else "index_failed"
            db.execute(text("""UPDATE kb_documents SET status='failed',error_code=:code,payload=NULL
                WHERE id=:id"""), {"id": row.id, "code": code})
        finally:
            stage.unlink(missing_ok=True)
    return True


def listen():
    """Получает уведомления и подбирает задания после перезапуска."""
    with psycopg.connect(KB_DSN, autocommit=True) as listener:
        listener.execute("LISTEN kb_changes")
        while True:
            if not process_one():
                for _ in listener.notifies(timeout=5, stop_after=1):
                    break


if __name__ == "__main__":
    if sys.argv[1:] == ["init"]:
        initialize()
    else:
        listen()
