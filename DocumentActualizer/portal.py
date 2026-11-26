import hashlib
import re
from pathlib import PurePosixPath
from urllib.parse import parse_qs, unquote, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

PAGE = "https://www.volgatech.net/about_the_university/documents/"
LIMIT = 48 * 1024 * 1024


def portal_url(base, link):
    """Разрешает только HTTPS-ссылки университета."""
    try:
        url = urlsplit(urljoin(base, link))
        host = url.hostname or ""
        port = url.port
    except ValueError:
        return None
    if url.scheme not in {"http", "https"} or url.username or url.password or port not in (None, 443):
        return None
    if host != "volgatech.net" and not host.endswith(".volgatech.net"):
        return None
    return urlunsplit(("https", url.netloc, url.path, url.query, ""))


def pdf_name(url, anchor):
    """Находит имя PDF в пути, параметрах или атрибуте скачивания."""
    parts = urlsplit(url)
    names = [anchor.get("download", ""), unquote(parts.path)]
    for values in parse_qs(parts.query).values():
        names.extend(values)
    for name in names:
        if name.casefold().endswith(".pdf"):
            return PurePosixPath(name).name
    if anchor.get("type", "").lower() == "application/pdf":
        return "document.pdf"
    return None


def official_title(anchor, filename):
    """Выбирает подпись ссылки или окружающего её элемента."""
    titles = [anchor.get_text(" ", strip=True), anchor.get("title", ""), anchor.get("aria-label", "")]
    image = anchor.find("img", alt=True)
    if image:
        titles.append(image["alt"])
    parent = anchor.find_parent(["li", "tr", "p"])
    if parent and len(parent.find_all("a", href=True)) == 1:
        caption = parent.get_text(" ", strip=True).replace(filename, "")
        titles.append(re.sub(r"\(?\.?pdf\)?|скачать|открыть", "", caption, flags=re.I).strip(" —:.-"))
    for value in titles:
        title = " ".join(value.split())
        if not re.search(r"[а-яёa-z]{3}", title, re.I) or title.lower().endswith(".pdf"):
            continue
        if not re.fullmatch(r"(скачать|открыть|смотреть|файл|pdf|download)(\s+(файл|pdf|документ))?", title, re.I):
            return title
    return None


def listing(html):
    """Извлекает ссылки и официальные названия независимо от CSS-классов."""
    documents = {}
    for anchor in BeautifulSoup(html, "html.parser").select("a[href]"):
        url = portal_url(PAGE, anchor["href"])
        if not url:
            continue
        filename = pdf_name(url, anchor)
        if not filename:
            continue
        title = official_title(anchor, filename)
        if title:
            documents.setdefault(url, (title, filename))
    return documents


def fetch(url, sink=None, *, previous=None):
    """Читает PDF с ограничением размера и вычисляет SHA-256."""
    for _ in range(5):
        if not portal_url(PAGE, url):
            raise ValueError("portal_url")
        headers = {"If-None-Match": previous[1]} if previous and previous[0] and previous[1] else {}
        with requests.get(url, headers=headers, stream=True, allow_redirects=False, timeout=(8, 30)) as response:
            if response.status_code == 304 and headers:
                return previous
            if response.is_redirect:
                url = portal_url(url, response.headers["Location"])
                if not url:
                    raise ValueError("portal_url")
                continue
            response.raise_for_status()
            digest = hashlib.sha256()
            size = 0
            for block in response.iter_content(65536):
                if not size and not block.startswith(b"%PDF-"):
                    raise ValueError("invalid_pdf")
                size += len(block)
                if size > LIMIT:
                    raise ValueError("too_large")
                digest.update(block)
                if sink:
                    sink.write(block)
            if not size:
                raise ValueError("empty_pdf")
            return digest.hexdigest(), response.headers.get("ETag")
    raise ValueError("portal_redirect")
