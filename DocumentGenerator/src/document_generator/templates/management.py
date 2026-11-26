from uuid import uuid4

import requests
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from . import database as store
from .pdf_form import convert_pdf
from .portal import PortalCatalog, download
from .schemas import Identifier
from .word import Edit, WordForm

router = APIRouter(prefix="/templates")
portal = PortalCatalog()
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ComponentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=160)
    required: bool = True
    question: str | None = Field(default=None, max_length=500)


class FieldSettings(ComponentInput):
    key: Identifier


class TemplateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=500)
    revision: int = Field(ge=0)
    edits: list[Edit] = Field(max_length=2000)
    fields: list[FieldSettings] = Field(default_factory=list, max_length=500)


def current_catalog():
    """Получает доступные для скачивания бланки."""
    try:
        return portal.current()
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(502, "Каталог МФЦ временно недоступен.") from error


@router.get("/catalog")
def catalog():
    """Отмечает бланки, по которым уже составлен шаблон."""
    items = current_catalog()
    with store.connect() as db:
        rows = db.execute("SELECT source_url,filename,id FROM form_templates").fetchall()
    imported = {row["source_url"] or row["filename"]: row["id"] for row in rows}
    return [dict(item, template=imported.get(item["url"]) or imported.get(item["filename"])) for item in items.values()]


@router.post("/catalog/{source}/import")
def import_form(source: str):
    """Сохраняет оригинал и открывает черновик бланка."""
    item = current_catalog().get(source)
    if not item:
        raise HTTPException(404, "Бланк отсутствует в каталоге МФЦ.")
    with store.connect() as db:
        existing = db.execute("""SELECT id FROM form_templates WHERE source_url=%s
            OR (source_url IS NULL AND filename=%s) ORDER BY source_url NULLS LAST LIMIT 1""",
                              (item["url"], item["filename"])).fetchone()
    if existing:
        return existing
    content, draft = read_source(item)
    with store.connect() as db:
        return save_source(db, item, content, draft)


def read_source(item):
    """Скачивает и проверяет исходный бланк."""
    try:
        content = download(item["url"], 12 * 1024 * 1024)
    except requests.RequestException as error:
        raise HTTPException(502, "Не удалось скачать бланк с портала.") from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    try:
        draft = None
        if item["filename"].casefold().endswith(".pdf"):
            draft = convert_pdf(content)
        else:
            WordForm(content)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return content, draft


def save_source(db, item, content, draft):
    """Связывает оригинал бланка с редактируемой копией."""
    added = db.execute("""INSERT INTO form_templates(id,source_url,filename,original,title,description)
        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(source_url) DO NOTHING RETURNING id""",
                       ("form_" + uuid4().hex, item["url"], item["filename"], content,
                        item["title"], item["title"])).fetchone()
    if not added:
        return db.execute("SELECT id FROM form_templates WHERE source_url=%s", (item["url"],)).fetchone()
    if draft:
        store.version(db, added["id"], 0, item["title"], draft, [])
    return added


@router.get("")
def library():
    """Перечисляет опубликованные шаблоны и черновики."""
    with store.connect() as db:
        return db.execute("SELECT id,title,revision,filename FROM form_templates ORDER BY title").fetchall()


@router.post("/components")
def add_component(data: ComponentInput):
    """Добавляет поле в общую библиотеку."""
    with store.connect() as db:
        return store.create_component(db, data.label, data.required, data.question or None)


def get_form(db, key, lock=False):
    """Открывает опубликованный DOCX или скачанный оригинал."""
    query = """SELECT t.id,t.title,t.revision,t.filename,coalesce(v.content,t.original) AS content
        FROM form_templates t LEFT JOIN form_versions v ON t.id=v.template_id AND v.revision=t.revision
        WHERE t.id=%s"""
    row = db.execute(query + (" FOR UPDATE OF t" if lock else ""), (key,)).fetchone()
    if not row:
        raise HTTPException(404, "Шаблон не найден.")
    return row


@router.get("/{key}/editor")
def editor(key: str):
    """Возвращает абзацы и компоненты для редактора."""
    with store.connect() as db:
        row = get_form(db, key)
        fields = available_fields(db, key, row["revision"])
    form = WordForm(row.pop("content"))
    return dict(row, blocks=form.blocks(), components=list(fields.values()))


@router.get("/{key}/source")
def source_file(key: str):
    """Возвращает исходный файл шаблона."""
    with store.connect() as db:
        row = db.execute("SELECT original,filename FROM form_templates WHERE id=%s", (key,)).fetchone()
    if not row:
        raise HTTPException(404, "Бланк не найден.")
    mime = "application/pdf" if row["filename"].casefold().endswith(".pdf") else DOCX
    return Response(row["original"], media_type=mime)


def available_fields(db, key, revision):
    """Учитывает настройки компонента в текущем бланке."""
    fields = store.components(db)
    for binding in store.bindings(db, key, revision):
        fields[binding["component_key"]] = binding["field"]
    return fields


def edited(db, key, data, lock=False):
    """Проверяет версию и вносит изменения в копию DOCX."""
    row = get_form(db, key, lock)
    if row["revision"] != data.revision:
        raise HTTPException(409, "Другой сотрудник сохранил изменения. Откройте шаблон заново.")
    form = WordForm(row["content"])
    components = available_fields(db, key, data.revision)
    try:
        for change in data.fields:
            if change.key not in components:
                raise ValueError("Неизвестный компонент.")
            components[change.key].update(label=change.label, required=change.required, question=change.question or None)
        form.edit(data.edits, components)
        if set(form.keys()) - components.keys():
            raise ValueError("Документ содержит неизвестный компонент.")
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return form, components


@router.post("/{key}/preview")
def preview(key: str, data: TemplateInput):
    """Показывает копию бланка с названиями полей."""
    with store.connect() as db:
        form, fields = edited(db, key, data)
        form.fill({k: "«" + fields[k]["label"] + "»" for k in form.keys()})
    return Response(form.serialize(), media_type=DOCX)


@router.post("/{key}/publish")
def publish(key: str, data: TemplateInput):
    """Публикует DOCX и связи компонентов одной транзакцией."""
    with store.connect() as db:
        form, configured = edited(db, key, data, lock=True)
        keys = form.keys()
        if not keys:
            raise HTTPException(422, "Добавьте в бланк хотя бы один компонент.")
        shared = store.components(db)
        fields = [(key, {k: v for k, v in configured[key].items() if v != shared[key].get(k)}) for key in keys]
        store.version(db, key, data.revision + 1, data.title, form.serialize(), fields)
    return {"id": key, "revision": data.revision + 1}
