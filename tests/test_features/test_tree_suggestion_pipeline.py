import re
from pathlib import Path
from uuid import uuid4

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from iaEditais.features.tree_suggestion.extraction import extract_document
from iaEditais.features.tree_suggestion.sections import (
    build_sections_tree,
    flatten_sections,
)
from iaEditais.features.tree_suggestion.text import (
    EvidenceLocator,
    build_batches,
    build_text_units,
    find_similar_title,
    normalize_title,
)

BODY = (
    'Registro de Precos para o fornecimento de reagentes de laboratorio, '
    'conforme especificacoes do Anexo I, com entrega em ate 30 dias.'
)
LINE_LIMIT = 80
TOTAL_DE_PAGINAS = 2
TAMANHO_LOTE = 400
PONTUACAO_EXATA = 100


def _wrap(text: str) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate) > LINE_LIMIT:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_paragraph(
    pdf: canvas.Canvas, text: str, x: float, y: float, leading: float = 15
) -> None:
    pdf.setFont('Helvetica', 10)
    for offset, line in enumerate(_wrap(text)):
        pdf.drawString(x, y - offset * leading, line)


def _build_pdf(path: Path) -> Path:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(60, height - 80, '1. OBJETO')
    _draw_paragraph(pdf, BODY, 60, height - 110)

    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(60, height - 170, '1.1 Itens incluidos')
    _draw_paragraph(
        pdf,
        'Sao incluidos os kits de coleta, reagentes e controles.',
        60,
        height - 195,
    )

    pdf.showPage()

    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(60, height - 80, '2. CONDICOES DE EXECUCAO')
    _draw_paragraph(
        pdf,
        'A entrega devera ser feita na unidade de saude indicada no item 3.',
        60,
        height - 110,
    )
    pdf.save()
    return path


@pytest.fixture
def pdf_path(tmp_path) -> Path:
    return _build_pdf(tmp_path / 'edital.pdf')


def test_extract_document_reads_text_and_pages(pdf_path):
    document = extract_document(str(pdf_path))

    assert len(document.page_map) == TOTAL_DE_PAGINAS
    assert 'OBJETO' in document.text
    assert 'CONDICOES DE EXECUCAO' in document.text
    assert document.lines
    assert any(line.bold for line in document.lines)
    assert all(
        document.text[line.char_start :].startswith(line.text)
        for line in document.lines
    )


def test_build_sections_tree_detects_headings(pdf_path):
    document = extract_document(str(pdf_path))
    sections = build_sections_tree(document)
    titles = [section.title for section in flatten_sections(sections)]

    assert any('OBJETO' in title for title in titles)
    assert any('CONDICOES DE EXECUCAO' in title for title in titles)

    child = next(
        section
        for section in flatten_sections(sections)
        if 'Itens incluidos' in section.title
    )
    assert child.parent_title is not None
    assert 'OBJETO' in child.parent_title


def test_build_text_units_covers_document(pdf_path):
    document = extract_document(str(pdf_path))
    sections = build_sections_tree(document)
    units = build_text_units(document.text, sections)

    assert units
    assert units[0].char_start == 0
    for unit in units:
        assert unit.char_end > unit.char_start
        assert document.text[unit.char_start : unit.char_end].strip()
    for previous, current in zip(units, units[1:]):
        assert previous.char_end == current.char_start


def test_build_batches_respects_budget(pdf_path):
    document = extract_document(str(pdf_path))
    sections = build_sections_tree(document)
    units = build_text_units(document.text, sections)

    batches = build_batches(document.text, units, TAMANHO_LOTE)

    assert batches
    assert all(
        batch.char_end - batch.char_start <= TAMANHO_LOTE for batch in batches
    )
    assert batches[0].char_start == units[0].char_start


def test_evidence_locator_finds_literal_quote(pdf_path):
    document = extract_document(str(pdf_path))
    locator = EvidenceLocator(document.text, document.page_map, 90)

    match = locator.locate('entrega em ate 30 dias')

    assert match is not None
    assert match.score == PONTUACAO_EXATA
    assert match.pages == [1]
    assert 'entrega em ate 30 dias' in document.text[
        match.char_start : match.char_end
    ]


def test_evidence_locator_rejects_unknown_quote(pdf_path):
    document = extract_document(str(pdf_path))
    locator = EvidenceLocator(document.text, document.page_map, 90)

    assert locator.locate('licitacao inexistente de teste') is None


def test_evidence_locator_finds_quote_on_second_page(pdf_path):
    document = extract_document(str(pdf_path))
    locator = EvidenceLocator(document.text, document.page_map, 90)

    match = locator.locate('unidade de saude indicada no item 3')

    assert match is not None
    assert match.pages == [2]


def test_normalize_title_and_find_similar():
    assert normalize_title('Objeto da Licitação') == 'objeto da licitacao'

    entity_id = uuid4()
    found = find_similar_title(
        'objeto da licitacao', [(entity_id, 'Objeto da Licitação')]
    )

    assert found is not None
    assert found[0] == entity_id
    assert find_similar_title('outro', [(entity_id, 'Objeto')]) is None


def test_document_text_has_no_control_characters(pdf_path):
    document = extract_document(str(pdf_path))

    assert re.search(r'\x00', document.text) is None
