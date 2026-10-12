import re
from pathlib import Path

class TextSanitizer:
    """Класс для очистки текста и Markdown-файлов от OCR-мусора, формул и артефактов."""

    def __init__(self) -> None:
        # Поиск HTML-комментариев с тегом картинки
        self.image_tag_pattern: re.Pattern[str] = re.compile(
            r'<!--\s*image\s*-->', 
            re.IGNORECASE
        )

        # Поиск HTML-комментариев с тегом нераскодированной формулы
        self.formula_tag_pattern: re.Pattern[str] = re.compile(
            r'<!--\s*formula-not-decoded\s*-->', 
            re.IGNORECASE
        )

        # Поиск отдельно стоящих спецсимволов вроде |, _, ^, ~, №, \
        self.ocr_trash_pattern: re.Pattern[str] = re.compile(
            r'(?<![#\-\d])\b[|_^~№\\\\]+\b|\s+[|_^~\\\\]+(?=\s+|$)'
        )

        # Поиск пустых строк или строк, состоящих только из пробелов и спецсимволов
        self.empty_trash_lines_pattern: re.Pattern[str] = re.compile(
            r'^\s*[|_^~\\\-]*\s*$', 
            re.MULTILINE
        )


        self.multi_newline_pattern: re.Pattern[str] = re.compile(r'\n{3,}')

    def sanitize_text(self, text: str) -> str:
        """Очищает строку текста от артефактов, формул и OCR-мусора."""
        if not text:
            return ""

        cleaned = self.image_tag_pattern.sub('', text)
        cleaned = self.formula_tag_pattern.sub('', cleaned)

        cleaned = self.empty_trash_lines_pattern.sub('', cleaned)

        cleaned = self.ocr_trash_pattern.sub('', cleaned)

        cleaned = self.multi_newline_pattern.sub('\n\n', cleaned)
        
        return cleaned.strip()

    def sanitize_file(self, file_path: Path) -> None:
        """Считывает файл, очищает его содержимое и перезаписывает обратно."""
        if not file_path.exists():
            return

        text = file_path.read_text(encoding="utf-8")
        cleaned_text = self.sanitize_text(text)
        
        file_path.write_text(cleaned_text + '\n', encoding="utf-8")
