from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from ..templates.schemas import FieldValue


class DialogState(StrEnum):
    IDLE = "IDLE"
    TEMPLATE_SUGGESTED = "TEMPLATE_SUGGESTED"
    COLLECTING_DATA = "COLLECTING_DATA"
    REVIEW = "REVIEW"
    GENERATED = "GENERATED"
    CANCELLED = "CANCELLED"


@dataclass
class DialogSession:
    id: str = field(default_factory=lambda: uuid4().hex)
    state: DialogState = DialogState.IDLE
    template_id: str | None = None
    candidates: list[str] = field(default_factory=list)
    values: dict[str, FieldValue] = field(default_factory=dict)
    message: str = "Какое заявление нужно оформить?"
    output_path: Path | None = None
    initial_messages: list[str] = field(default_factory=list, repr=False)
