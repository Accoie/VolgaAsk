import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from ..utils.date_parser import DateParser

SECTION_PATTERN: re.Pattern[str] = re.compile(r'^(#{2,3})\s+(.+)$')

# "1. ", "3.6. ", "- 1.2. ", "4.20. " 
# Не является артиклем "1)", "2) ", "1.7 ", или номера среди предложения.
ARTICLE_PATTERN: re.Pattern[str] = re.compile(r'^(?:-\s*)?(\d+(?:\.\d+)*)\.(?:\s+|$)')


@dataclass
class ChunkState:
    """Состояние обработки одного Markdown-файла."""
    heading2: str | None = None
    heading3: str | None = None
    text: list[str] = field(default_factory=list)


class Chunker:
    """Разбивает Markdown на чанки."""

    def __init__(self, min_chunk_length: int = 50) -> None:
        self.min_chunk_length: int = min_chunk_length

    def chunk(self, md_file: Path, output_dir: Path) -> Path:
        """Разбивает один .md на чанки и возвращает файл в формате json."""
        document_id: str = md_file.stem
        document_date: str | None = DateParser.extract_document_date(md_file)
        chunks: list[dict] = list(
            self._extract_chunk(md_file, document_id, document_date)
        )

        output_file: Path = output_dir / f"{document_id}.json"
        output_file.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_file

    def _extract_chunk(
        self,
        md_file: Path,
        document_id: str,
        document_date: str | None,
    ) -> Iterator[dict]:
        state: ChunkState = ChunkState()
        chunk_index: int = 0

        with md_file.open(encoding="utf-8") as f:
            for line in f:
                line_str: str = line.rstrip('\n')

                trimmed_line: str = line_str.strip()

                is_section: bool = self._is_section(line_str)
                is_article: bool = self._is_article_start(trimmed_line)

                if is_section or is_article:
                    chunk: dict | None = self._build_chunk(
                        state, document_id, document_date, chunk_index
                    )
                    
                    if chunk:
                        yield chunk
                        chunk_index += 1
                        state.text = []
                    elif is_section:
                        state.text = []

                    if is_section:
                        self._update_headings(state, line_str)
                        continue

                state.text.append(line_str)

        chunk: dict | None = self._build_chunk(
            state, document_id, document_date, chunk_index
        )
        if chunk:
            yield chunk

    def _is_section(self, line: str) -> bool:
        """Проверяет является ли строка заголовком ## или ###."""
        return bool(SECTION_PATTERN.match(line))

    def _is_article_start(self, line: str) -> bool:
        """Проверяет является ли строка началом подлинного пункта/статьи."""
        return bool(ARTICLE_PATTERN.match(line))

    def _update_headings(self, state: ChunkState, line: str) -> None:
        """Обновить текущие заголовки."""
        match: re.Match[str] | None = SECTION_PATTERN.match(line)
        if not match:
            return

        level: int = len(match.group(1))
        title: str = match.group(2).strip()

        if level == 2:
            state.heading2 = title
            state.heading3 = None
        else:
            state.heading3 = title

    def _build_chunk(
        self,
        state: ChunkState,
        document_id: str,
        document_date: str | None,
        chunk_index: int,
    ) -> dict | None:
        """Собрать чанк из state."""
        text: str = '\n'.join(state.text).strip()
        if not text or len(text) < self.min_chunk_length:
            return None

        return self._make_chunk(
            text, document_id, document_date, state, chunk_index
        )

    def _make_chunk(
        self,
        text: str,
        document_id: str,
        document_date: str | None,
        state: ChunkState,
        chunk_index: int,
    ) -> dict:
        """Собрать словарь чанка."""
        return {
            "text": text,
            "document_id": document_id,
            "document_date": document_date,
            "article": self._extract_article(text),
            "heading": self._merge_headings(state),
            "chunk_index": chunk_index,
        }

    def _extract_article(self, text: str) -> str | None:
        """Извлечь точный номер пункта из начала текста чанка."""
        first_line = text.split('\n')[0].strip()
        match: re.Match[str] | None = ARTICLE_PATTERN.match(first_line)
        return match.group(1) if match else None

    def _merge_headings(self, state: ChunkState) -> str | None:
        """Склеить заголовки H2 и H3 в строку «H2 > H3»."""
        return ' > '.join(
            filter(None, [state.heading2, state.heading3])
        ) or None
