import argparse
from time import sleep

from .anonymizer import DocumentAnonymizer


def main():
    """Публикует обезличенную копию до истечения срока."""
    parser = argparse.ArgumentParser(description="Обезличивание текстовых DOCX")
    parser.add_argument("source", help="Локальный путь или ссылка на DOCX")
    parser.add_argument("--ttl", type=int, default=300, help="Срок действия ссылки в секундах")
    args = parser.parse_args()
    try:
        with DocumentAnonymizer(args.ttl) as service:
            print(service.anonymize(args.source), flush=True)
            sleep(args.ttl)
    except KeyboardInterrupt:
        return
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Не удалось обезличить документ ({type(error).__name__}).\n")


if __name__ == "__main__":
    main()
