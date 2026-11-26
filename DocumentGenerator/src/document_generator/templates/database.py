import os
import re
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ..errors import DocumentError
from .registry import TemplateRegistry
from .schemas import DocumentTemplate, TemplateChoice

DDL = """
CREATE TABLE IF NOT EXISTS form_templates (
    id text PRIMARY KEY, source_url text UNIQUE, filename text NOT NULL, original bytea NOT NULL,
    title text NOT NULL, description text NOT NULL, aliases text[] NOT NULL DEFAULT '{}',
    protected_fields text[] NOT NULL DEFAULT '{}', revision integer NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS form_versions (
    template_id text REFERENCES form_templates, revision integer NOT NULL, title text NOT NULL,
    content bytea NOT NULL, PRIMARY KEY(template_id,revision)
);
CREATE TABLE IF NOT EXISTS form_components (
    key text PRIMARY KEY, definition jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS form_template_components (
    template_id text NOT NULL, revision integer NOT NULL, component_key text REFERENCES form_components,
    position integer NOT NULL, overrides jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY(template_id,revision,component_key), UNIQUE(template_id,revision,position),
    FOREIGN KEY(template_id,revision) REFERENCES form_versions
);
"""


def connect():
    """Открывает соединение с каталогом шаблонов."""
    return psycopg.connect(os.environ["TEMPLATE_DSN"], row_factory=dict_row)


def version(db, template_id, revision, title, content, fields):
    """Записывает версию бланка и её упорядоченные компоненты."""
    db.execute("INSERT INTO form_versions VALUES (%s,%s,%s,%s)", (template_id, revision, title, content))
    for position, (key, overrides) in enumerate(fields):
        db.execute("INSERT INTO form_template_components VALUES (%s,%s,%s,%s,%s)",
                   (template_id, revision, key, position, Jsonb(overrides)))
    db.execute("UPDATE form_templates SET title=%s,revision=%s WHERE id=%s", (title, revision, template_id))


def seed(db, template):
    """Переносит штатный бланк и сохраняет его правила заполнения."""
    content = template.path.read_bytes()
    filename = template.source_document or template.id + ".docx"
    added = db.execute("""INSERT INTO form_templates(id,filename,original,title,description,aliases,protected_fields)
               VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING RETURNING id""",
               (template.id, filename, content, template.title, template.description,
                template.aliases, template.protected_fields)).fetchone()
    if not added:
        db.execute("UPDATE form_templates SET filename=%s WHERE id=%s AND source_url IS NULL", (filename, template.id))
        return
    fields = []
    for field in template.fields:
        definition = field.model_dump()
        db.execute("INSERT INTO form_components VALUES (%s,%s) ON CONFLICT DO NOTHING",
                   (field.key, Jsonb(definition)))
        base = db.execute("SELECT definition FROM form_components WHERE key=%s", (field.key,)).fetchone()
        fields.append((field.key, {k: v for k, v in definition.items() if v != base["definition"].get(k)}))
    version(db, template.id, 1, template.title, content, fields)


def initialize(directory):
    """Однократно импортирует существующий каталог в PostgreSQL."""
    with connect() as db:
        db.execute("SELECT pg_advisory_xact_lock(384712981)")
        db.execute(DDL)
        db.execute("CREATE TABLE IF NOT EXISTS form_migrations (name text PRIMARY KEY)")
        if db.execute("SELECT 1 FROM form_migrations WHERE name='import_source_forms'").fetchone():
            return
        legacy = TemplateRegistry(directory)
        if legacy.unavailable:
            raise DocumentError("Не удалось перенести шаблоны: " + ", ".join(legacy.unavailable))
        for template in legacy.list_templates():
            seed(db, template)
        db.execute("INSERT INTO form_migrations VALUES ('import_source_forms')")


def components(db):
    """Загружает библиотеку компонентов."""
    rows = db.execute("SELECT key,definition FROM form_components ORDER BY definition->>'label',key")
    return {row["key"]: row["definition"] for row in rows}


def create_component(db, label, required, question):
    """Создаёт общее поле с независимым ключом."""
    key = "field_" + uuid4().hex
    definition = dict(key=key, type="string", label=label, required=required, question=question)
    db.execute("INSERT INTO form_components VALUES (%s,%s)", (key, Jsonb(definition)))
    return definition


def bindings(db, template_id, revision):
    """Возвращает настройки полей конкретной версии."""
    return db.execute("""SELECT component_key,overrides,definition || overrides AS field
        FROM form_template_components JOIN form_components ON key=component_key
        WHERE template_id=%s AND revision=%s ORDER BY position""", (template_id, revision)).fetchall()


class DbRegistry:
    def list_templates(self):
        """Предлагает только опубликованные версии бланков."""
        with connect() as db:
            rows = db.execute("""SELECT CASE WHEN revision=1 THEN id ELSE id || '__v' || revision END AS id,
                              title,description,aliases FROM form_templates
                              WHERE revision>0 ORDER BY title""").fetchall()
        return [TemplateChoice(**row) for row in rows]

    def get(self, template_id):
        """Открывает версию, выбранную в начале диалога."""
        match = re.fullmatch(r"([a-z][a-z0-9_]*?)__v(\d+)", template_id or "")
        key, revision = (match[1], int(match[2])) if match else (template_id, 1)
        with connect() as db:
            row = db.execute("""SELECT v.title,v.content,t.description,t.aliases,t.protected_fields
                FROM form_versions v JOIN form_templates t ON t.id=v.template_id
                WHERE v.template_id=%s AND v.revision=%s""", (key, revision)).fetchone()
            if not row:
                raise DocumentError("Шаблон недоступен.")
            fields = [item["field"] for item in bindings(db, key, revision)]
        return DocumentTemplate(id=template_id, fields=fields, **row)
