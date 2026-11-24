import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from volgaask_document_templates import __file__ as templates_file


@dataclass(frozen=True)
class Settings:
    templates_dir: Path = Path(templates_file).parent
    output_dir: Path = Path("output")
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    @classmethod
    def from_env(cls) -> "Settings":
        """Читает настройки приложения."""
        load_dotenv(Path.cwd() / ".env")
        return cls(
            output_dir=Path(os.getenv("DOCUMENT_OUTPUT_DIR", "output")),
            ollama_host=os.getenv("OLLAMA_HOST", cls.ollama_host),
            ollama_model=os.getenv("OLLAMA_MODEL", cls.ollama_model),
        )
