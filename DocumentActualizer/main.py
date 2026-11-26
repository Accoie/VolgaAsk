import logging
import os
import time

import psycopg
import requests

from portal import PAGE, fetch, listing


def synchronize(db):
    """Обновляет список портала и проверяет содержимое каждого PDF."""
    page = requests.get(PAGE, timeout=30)
    page.raise_for_status()
    entries = listing(page.content)
    if not entries:
        raise ValueError("На странице не найдено документов")
    with db.transaction():
        db.execute("UPDATE kb_catalog SET available=false WHERE NOT (url=ANY(%s))", (list(entries),))
        for url, (title, filename) in entries.items():
            db.execute("""INSERT INTO kb_catalog(url,title,filename) VALUES (%s,%s,%s)
                ON CONFLICT(url) DO UPDATE SET title=excluded.title, filename=excluded.filename,
                available=true""", (url, title, filename))
    errors = 0
    for url in entries:
        try:
            previous = db.execute("SELECT checksum,etag FROM kb_catalog WHERE url=%s", (url,)).fetchone()
            checksum, etag = fetch(url, previous=previous)
        except (requests.RequestException, ValueError):
            checksum = None
            etag = None
            errors += 1
        db.execute("UPDATE kb_catalog SET checksum=%s,etag=%s WHERE url=%s", (checksum, etag, url))
    return f"Не удалось прочитать PDF: {errors}" if errors else None


def main():
    """Периодически обновляет каталог, сохраняя предыдущий при сбое сайта."""
    while True:
        with psycopg.connect(os.environ["KB_DSN"], autocommit=True) as db:
            try:
                warning = synchronize(db)
                db.execute("""INSERT INTO kb_sync(refreshed,error) VALUES(now(),%s)
                    ON CONFLICT(id) DO UPDATE SET refreshed=now(),error=excluded.error""", (warning,))
            except (ValueError, requests.RequestException):
                logging.exception("Ошибка обновления каталога")
                db.execute("""INSERT INTO kb_sync(error) VALUES ('Портал временно недоступен')
                    ON CONFLICT(id) DO UPDATE SET error=excluded.error""")
        time.sleep(3600)


if __name__ == "__main__":
    main()
