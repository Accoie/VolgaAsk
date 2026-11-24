from .dialog.session import DialogState
from .service import DocumentGenerator


def main() -> None:
    """Запускает диалог в терминале."""
    generator = DocumentGenerator()
    print("VolgaAsk Document Generator")
    if generator.registry.unavailable:
        print("Пропущены повреждённые шаблоны: " + ", ".join(generator.registry.unavailable))
    if not generator.registry.list_templates():
        print("Нет доступных бланков. Проверь папку шаблонов.")
        return
    print("Какое заявление нужно оформить? Для выхода напиши «отмена».")
    try:
        session = generator.start(input("Вы: "))
        print("DG:", session.message)
        while session.state not in {DialogState.CANCELLED, DialogState.GENERATED}:
            session = generator.send_message(session.id, input("Вы: "))
            print("DG:", session.message)
    except (EOFError, KeyboardInterrupt):
        print("\nДиалог завершён.")


if __name__ == "__main__":
    main()
