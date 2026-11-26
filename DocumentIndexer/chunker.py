import logging
import re

from docling_core.transforms.chunker.doc_chunk import DocChunk
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc.document import DoclingDocument
from transformers import AutoTokenizer

from encoder import load_model

logger = logging.getLogger(__name__)

AMEDMENT_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"о\s+внесени\w*\s+изменени\w*", re.IGNORECASE),
    re.compile(r"внесени\w*\s+изменени\w*", re.IGNORECASE),
]

class Chunker:
    """Разбивает DoclingDocument на чанки."""

    HEAD_LENGTH: int = 2000


    def __init__(
        self,
        model_name: str,
        max_tokens: int = 256,
    ) -> None:
        tokenizer = load_model(model_name, AutoTokenizer.from_pretrained, lambda model, path: model.save_pretrained(path))
        self.chunker = HybridChunker(
            tokenizer=HuggingFaceTokenizer(tokenizer=tokenizer, max_tokens=max_tokens), merge_peers=True)


    def chunk(
        self,
        doc: DoclingDocument,
        document_id: str,
    ) -> list[dict[str, object]]:
        """Разбивает документ на чанки и возвращает их с метаданными."""
        amendant = self._is_amendment(doc)
        chunks = list(self.chunker.chunk(dl_doc=doc))

        result: list[dict[str, object]] = []
        for chunk_index, chunk in enumerate(chunks):
            if not isinstance(chunk, DocChunk):
                raise TypeError(f"Unexpected chunk type: {type(chunk).__name__}")

            result.append(
                {
                    "text": self.chunker.contextualize(chunk=chunk),
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "amendant": amendant,
                    "headings": chunk.meta.headings or [],
                    "page_numbers": self._extract_page_numbers(chunk),
                }
            )

        logger.info("Document %s chunked into %d chunks, amendant=%s", document_id, len(result), amendant)
        return result


    def _is_amendment(self, doc: DoclingDocument) -> bool:
        """Определяет, является ли документ поправкой, по заголовку."""
        raw_head = doc.export_to_text()[:self.HEAD_LENGTH]

        return any(marker.search(raw_head) for marker in AMEDMENT_MARKERS)


    def _extract_page_numbers(self, chunk: DocChunk) -> list[int]:
        """Собирает и сортирует уникальные номера страниц, к которым относится чанк."""
        page_numbers = {
            provenance.page_no
            for item in chunk.meta.doc_items
            for provenance in item.prov or []
        }
        return sorted(page_numbers)
