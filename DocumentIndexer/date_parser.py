import re


class DateParser:
    """Извлекает дату документа из имени файла."""

    @staticmethod
    def parse_data_from_text(text: str) -> str | None:
        """Читает дату или год из имени файла."""
        match = re.match(r'^(\d{2})(\d{2})(\d{2})-', text)
        if match:
            return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"

        match = re.search(r'(\d{4})', text)
        if match:
            return f"{match.group(1)}-01-01"

        return None
