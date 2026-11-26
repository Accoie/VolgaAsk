import hashlib
from urllib.parse import urljoin, urlsplit

import requests


LIMIT = 48 * 1024 * 1024


def checked_url(url):
    """Разрешает скачивание по HTTPS с доменов университета."""
    address = urlsplit(url)
    host = address.hostname or ""
    if (address.scheme != "https" or address.username is not None or address.password is not None
            or address.port not in (None, 443) or not (host == "volgatech.net" or host.endswith(".volgatech.net"))):
        raise ValueError("portal_url")
    return url


def fetch_pdf(url, stream):
    """Скачивает PDF и вычисляет контрольную сумму исходного файла."""
    for _ in range(5):
        with requests.get(checked_url(url), stream=True, allow_redirects=False, timeout=(8, 30)) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["Location"])
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
                stream.write(block)
            if not size:
                raise ValueError("empty_pdf")
            return digest.hexdigest()
    raise ValueError("portal_redirect")
