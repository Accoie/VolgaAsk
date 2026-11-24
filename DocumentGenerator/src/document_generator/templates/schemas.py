from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import AliasChoices, BaseModel, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
FieldValue = str | int | bool


class Bounds(BaseModel):
    min: int | None = None
    max: int | None = None

    @model_validator(mode="after")
    def check_range(self) -> Self:
        """Проверяет границы диапазона."""
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("Неверный диапазон")
        return self


class TemplateField(BaseModel):
    key: Identifier = Field(validation_alias=AliasChoices("key", "name"))
    label: Text | None = None
    type: Literal["string", "date", "integer", "boolean", "choice", "enum"]
    required: bool = True
    question: Text
    options: list[Text] = Field(default_factory=list)
    constraints: Bounds = Field(default_factory=Bounds)
    default: FieldValue | None = None
    validation_hint: str = ""

    @model_validator(mode="after")
    def check_options(self) -> Self:
        """Проверяет варианты выбора."""
        options = {value.casefold() for value in self.options}
        if self.type in {"enum", "choice"} and not options:
            raise ValueError("Для поля выбора нужны варианты")
        if len(options) != len(self.options):
            raise ValueError("Варианты выбора повторяются")
        return self

    @property
    def caption(self) -> str:
        """Возвращает название поля для диалога."""
        return self.label or self.key


class TemplateSchema(BaseModel):
    id: Identifier
    title: Text = Field(validation_alias=AliasChoices("title", "name"))
    description: Text
    aliases: list[Text] = Field(default_factory=list)
    fields: list[TemplateField] = Field(min_length=1)
    protected_fields: list[Identifier] = Field(default_factory=list)
    template_file: Literal["template.docx"] = "template.docx"

    @model_validator(mode="after")
    def check_keys(self) -> Self:
        """Проверяет ключи и служебные поля."""
        keys = {field.key for field in self.fields}
        if len(keys) != len(self.fields) or keys.intersection(self.protected_fields):
            raise ValueError("Повторяющиеся или служебные ключи")
        return self


class DocumentTemplate(TemplateSchema):
    path: Path
