import re
from pathlib import Path


HEAD_SIZE = 2000

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
    """Извлекает дату документа из текста."""

    @staticmethod
    def parse_data_from_text(text: str) -> str | None:
        """Дата из текста"""
        match = re.match(r'^(\d{2})(\d{2})(\d{2})-', text)
        if match:
            return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"

        match = re.search(r'(\d{4})', text)
        if match:
            return f"{match.group(1)}-01-01"

        return None