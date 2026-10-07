import re
from pathlib import Path


HEAD_SIZE = 3000

DATE_PATTERNS = [
    r'от\s+(\d{1,2}\s+[а-яё]+\s+\d{4})',
    r'(\d{2}\.\d{2}\.\d{4})',
    r'записи от (\d{2}\.\d{2}\.\d{4})',
]

MONTHS = {
    'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
    'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
    'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12',
}


class DateParser:
    """Извлекает дату документа из имени файла или текста."""

    @staticmethod
    def extract_document_date(md_file: Path) -> str | None:
        """Приоритет: имя файла -> текст -> None."""
        date_from_name = DateParser.from_filename(md_file.name)
        if date_from_name:
            return date_from_name

        return DateParser.from_file(md_file)

    @staticmethod
    def from_filename(filename: str) -> str | None:
        """Дата из имени файла."""
        match = re.match(r'^(\d{2})(\d{2})(\d{2})-', filename)
        if match:
            return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"

        match = re.search(r'(\d{4})', filename)
        if match:
            return f"{match.group(1)}-01-01"

        return None

    @staticmethod
    def from_file(md_file: Path) -> str | None:
        """Дата из первых N символов файла."""
        with md_file.open(encoding="utf-8") as f:
            head = f.read(HEAD_SIZE)

        return DateParser.from_text(head)

    @staticmethod
    def from_text(text: str) -> str | None:
        """Дата из текста."""
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return DateParser._parse_russian_date(match.group(1))
        return None

    @staticmethod
    def _parse_russian_date(raw: str) -> str | None:
        """«11 марта 2020» -> 2020-03-11."""
        raw = raw.strip()

        match = re.match(r'(\d{1,2})\s+([а-яё]+)\s+(\d{4})', raw, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            month = MONTHS.get(match.group(2).lower())
            year = match.group(3)
            if month:
                return f"{year}-{month}-{day}"

        match = re.match(r'(\d{2})\.(\d{2})\.(\d{4})', raw)
        if match:
            return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"

        return None