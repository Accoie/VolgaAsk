from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .schemas import ReviewError
from .service import DocumentReviewService

app = FastAPI()


class ReviewRequest(BaseModel):
    allow_external: bool = False


@app.post("/review/{chat_id}/{file_id}")
def review(chat_id: UUID, file_id: UUID, request: ReviewRequest):
    """Проверяет сохранённое заявление после локального обезличивания."""
    path = Path("/storage") / str(chat_id) / f"{file_id}.docx"
    if not path.is_file():
        raise HTTPException(404, "Документ не найден.")
    try:
        service = DocumentReviewService()
        if request.allow_external:
            return {"report": service.review(path, allow_external=True)}
        checked = service.check(path)
        return {"report": "Локальная проверка обезличивания пройдена." if checked.safe
                else "Локальная проверка обнаружила риск раскрытия данных."}
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(422, "Не удалось завершить проверку документа.") from exc
