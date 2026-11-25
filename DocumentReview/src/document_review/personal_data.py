import re
from secrets import choice


WORD = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?"
PATRONYMIC = r"[А-ЯЁ][а-яё]+(?:ович|евич|ич|овна|евна|ична)"
FULL_NAME = re.compile(rf"(?<!\w){WORD}\s+{WORD}\s+{PATRONYMIC}(?!\w)")
INITIALS = re.compile(rf"(?<!\w){WORD}\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.")
LABELED_NAME = re.compile(
    r"(?:ф\.?\s*и\.?\s*о\.?|заявитель)\s*(?:\(полностью\))?\s*[:—]?\s+"
    r"([а-яё-]+(?:\s+[а-яё-]+){1,2})\s*$", re.IGNORECASE
)
NAMES = (
    ("Сомов", "Артём", "Игоревич"),
    ("Кедров", "Борис", "Андреевич"),
    ("Луговой", "Олег", "Дмитриевич"),
)
FEMALE_NAMES = (
    ("Сомова", "Дарья", "Игоревна"),
    ("Кедрова", "Вера", "Андреевна"),
    ("Луговая", "Анна", "Дмитриевна"),
)


def fake_name(value: str) -> str:
    """Создаёт другое ФИО с тем же числом компонентов."""
    parts = value.split()
    names = FEMALE_NAMES if parts[-1].lower().endswith(("вна", "чна")) else NAMES
    if INITIALS.fullmatch(value):
        surname, first, middle = choice([n for n in names if n[0].lower() not in value.lower()])
        if value.split()[0].lower().endswith(("ову", "еву", "ину")):
            surname = surname + "у" if surname.endswith("ов") else "Луговому"
        return f"{surname} {first[0]}.{middle[0]}."
    options = [n for n in names if all(word.casefold() not in value.casefold() for word in n)]
    if not options:
        return " ".join(("Лесова", "Нина", "Романовна")[:len(parts)])
    return " ".join(choice(options)[:len(parts)])


def name_values(text: str):
    """Находит полные имена и фамилии с инициалами."""
    match = LABELED_NAME.search(text)
    if match:
        yield match.group(1)
    for pattern in (FULL_NAME, INITIALS):
        yield from (match.group() for match in pattern.finditer(text))


def protected_line(text: str) -> bool:
    """Распознаёт подписи и незаполненные строки бланка."""
    line = text.strip()
    return (
        not line or line.startswith("(") and line.endswith(")")
        or "_" in line or bool(re.fullmatch(r"[А-ЯЁA-Z.]{2,10}\s*:?", line))
    )
