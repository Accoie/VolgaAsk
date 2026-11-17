import re
from pathlib import Path


AMENDMENT_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"внесени\w*\s+изменени\w*", re.IGNORECASE),
    re.compile(r"изменени\w*\s+в\s+устав", re.IGNORECASE),
    re.compile(r"изложить\s+в\s+следующей\s+редакции", re.IGNORECASE),
    ##re.compile(r"признать\s+утратившим\s+силу", re.IGNORECASE),
   ## re.compile(r"дополнить\s+пунктом", re.IGNORECASE),
]


class DocumentTypeParser:
    """Определяет, является ли документ изменением."""

    HEAD_LENGTH: int = 2000

    @classmethod
    def is_amendment(cls, md_file: Path) -> bool:
        """Прочитать начало .md и проверить маркеры изменения."""
        head: str = cls._read_head(md_file)

        return any(
            marker.search(head)
            for marker in AMENDMENT_MARKERS
        )

    @classmethod
    def _read_head(cls, md_file: Path) -> str:
        """Прочитать первые HEAD_LENGTH символов файла."""
        with md_file.open(encoding="utf-8") as f:
            return f.read(cls.HEAD_LENGTH)
