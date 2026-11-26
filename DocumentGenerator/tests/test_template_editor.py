from io import BytesIO

from docx import Document

from document_generator.templates.word import Edit, WordForm


def test_component_in_formatted_text_and_table():
    """Проверяет повторную подстановку и оформление исходного DOCX."""
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("От ")
    paragraph.add_run("фами").bold = True
    paragraph.add_run("лия, студента")
    document.add_table(1, 1).cell(0, 0).text = "Подпись: ___"
    original = BytesIO()
    document.save(original)

    form = WordForm(original.getvalue())
    form.edit([Edit(paragraph=0, start=3, end=10, component="student"),
               Edit(paragraph=1, start=9, end=12, component="student")], {"student"})
    assert form.keys() == ["student"]
    saved = WordForm(form.serialize())
    saved.fill({"student": "Иванов & сын"})
    result = Document(BytesIO(saved.serialize()))
    assert result.paragraphs[0].text == "От Иванов & сын, студента"
    assert result.paragraphs[0].runs[1].bold
    assert result.tables[0].cell(0, 0).text == "Подпись: Иванов & сын"
