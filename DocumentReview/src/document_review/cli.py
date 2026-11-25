import argparse

from .schemas import ReviewError
from .service import DocumentReviewService


def main():
    """Запускает локальную проверку или разрешённое ревью."""
    parser = argparse.ArgumentParser(description="Проверка DOCX")
    parser.add_argument("source", help="Путь или ссылка на DOCX")
    parser.add_argument("--allow-external", action="store_true", help="Разрешить отправку копии в GigaChat")
    args = parser.parse_args()
    service = DocumentReviewService()
    try:
        if args.allow_external:
            print(service.review(args.source, allow_external=True))
        else:
            result = service.check(args.source)
            print(result.model_dump_json(indent=2))
    except (OSError, ValueError, ReviewError) as error:
        parser.exit(1, f"Проверка прервана: {error}\n")


if __name__ == "__main__":
    main()
