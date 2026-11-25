from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from secrets import token_urlsafe
from threading import Lock, Thread
from time import monotonic

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DownloadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Выдаёт документ по действующей ссылке."""
        data = self.server.lookup(self.path)
        if data is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", DOCX_TYPE)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", 'attachment; filename="anonymized.docx"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        """Исключает ссылки на документы из журнала."""


class TemporaryLinks(ThreadingHTTPServer):
    def __init__(self, ttl: int):
        """Запускает локальную выдачу документов из памяти."""
        if ttl < 1:
            raise ValueError("Срок действия ссылки должен быть положительным.")
        super().__init__(("127.0.0.1", 0), DownloadHandler)
        self.ttl = ttl
        self.files = {}
        self.lock = Lock()
        self.thread = Thread(target=self.serve_forever, daemon=True)
        self.thread.start()

    def publish(self, data: bytes) -> str:
        """Создаёт временную ссылку на готовый документ."""
        path = f"/documents/{token_urlsafe(32)}.docx"
        with self.lock:
            if not self.thread.is_alive():
                raise RuntimeError("Сервис выдачи остановлен.")
            self.files[path] = (monotonic() + self.ttl, data)
        return f"http://127.0.0.1:{self.server_port}{path}"

    def lookup(self, path: str) -> bytes | None:
        """Возвращает содержимое до истечения срока."""
        with self.lock:
            item = self.files.get(path)
            if item and item[0] > monotonic():
                return item[1]
        return None

    def service_actions(self):
        """Освобождает память истёкших ссылок."""
        now = monotonic()
        with self.lock:
            for path in [key for key, (expiry, _) in self.files.items() if expiry <= now]:
                del self.files[path]

    def close(self):
        """Останавливает выдачу и удаляет копии."""
        self.shutdown()
        self.thread.join()
        self.server_close()
        with self.lock:
            self.files.clear()
