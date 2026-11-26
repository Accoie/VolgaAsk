import hashlib
import re
from pathlib import PurePosixPath
from threading import Lock
from time import monotonic
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

PAGE = "https://news.volgatech.net/mfc_vlgtch/"
HOSTS = {"news.volgatech.net", "www.volgatech.net", "volgatech.net"}


def university_url(base, link):
    """Разрешает ссылки на публичные серверы университета."""
    try:
        parts = urlsplit(urljoin(base, link))
        if parts.scheme == "https" and parts.hostname in HOSTS and not parts.username and parts.port in (None, 443):
            return parts._replace(fragment="").geturl()
    except ValueError:
        return None
    return None


def download(url, limit):
    """Получает файл с проверкой адреса после перенаправлений."""
    for _ in range(5):
        with requests.get(url, stream=True, allow_redirects=False, timeout=(6, 15)) as response:
            if response.is_redirect:
                url = university_url(url, response.headers["Location"])
                if not url:
                    break
                continue
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > limit:
                    raise ValueError("Размер файла превышает допустимый.")
            return bytes(content)
    raise ValueError("Не удалось открыть ссылку МФЦ.")


def caption(link):
    """Соединяет подпись бланка с названием услуги."""
    title = re.sub(r"\s*(?:Форма\s*·\s*)?(?:DOCX|PDF)\s*$", "", link.get_text(" ", strip=True), flags=re.I)
    section = link.find_parent("details")
    heading = section.find("summary") if section else None
    if heading:
        service = heading.get_text(" ", strip=True)
        step = link.find_parent("li")
        if step and step.parent.name == "ol":
            number = len(step.find_previous_siblings("li")) + 1
            service += f" (вариант {number})"
        return service if title.casefold() in {"", "заявление", "скачать"} else f"{service} — {title}"
    return title or link.get("title", "")


def form_filename(url, link):
    """Находит имя бланка в адресе или атрибутах ссылки."""
    address = urlsplit(url)
    names = [link.get("download", ""), unquote(address.path)]
    names.extend(name for values in parse_qs(address.query).values() for name in values)
    label = link.get_text(" ", strip=True)
    for name in names:
        filename = PurePosixPath(name).name
        if filename.casefold().endswith(".docx"):
            return filename
        if filename.casefold().endswith(".pdf") and re.search(r"\b(?:форма|бланк|заявление|согласие)\b", label, re.I):
            return filename
    return None


def parse(html):
    """Собирает бланки независимо от CSS-классов портала."""
    items = {}
    for link in BeautifulSoup(html, "html.parser").select("a[href]"):
        url = university_url(PAGE, link["href"])
        if not url:
            continue
        filename = form_filename(url, link)
        if filename:
            key = hashlib.sha256(url.encode()).hexdigest()
            items[key] = dict(id=key, url=url, filename=filename, title=caption(link) or filename)
    if not items:
        raise ValueError("На странице МФЦ не найдены бланки.")
    return items


class PortalCatalog:
    def __init__(self):
        """Хранит последнюю выборку портала в памяти."""
        self.lock = Lock()
        self.items = {}
        self.expires = 0

    def current(self):
        """Обновляет каталог по запросу раз в пять минут."""
        with self.lock:
            if monotonic() >= self.expires:
                self.items = parse(download(PAGE, 4 * 1024 * 1024))
                self.expires = monotonic() + 300
            return self.items
