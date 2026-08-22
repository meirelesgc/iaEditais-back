import fitz

from iaEditais.services.vector_service import (
    MAX_CHARS_PER_CHUNK,
    _pdf_to_documents,
)


def _create_sample_pdf(path):
    pdf = fitz.open()
    page = pdf.new_page()
    y = 72
    for i in range(30):
        page.insert_text(
            (72, y),
            f'Linha {i} com texto suficiente para testar o agrupamento',
        )
        y += 14
    page.insert_text((72, y), '8 - Documentacao de habilitacao')
    y += 14
    page.insert_text((72, y), 'Conteudo inicial da secao oito do edital')

    page_two = pdf.new_page()
    page_two.insert_text(
        (72, 72), 'Continuacao do texto na segunda pagina'
    )

    pdf.save(path)
    pdf.close()


def test_chunks_carry_source_ids_indexes_and_pages(tmp_path):
    pdf_path = tmp_path / 'edital_teste.pdf'
    _create_sample_pdf(str(pdf_path))

    documents = _pdf_to_documents(str(pdf_path))

    assert documents

    sources = {doc.metadata['source'] for doc in documents}
    assert sources == {'iaEditais/storage/uploads/edital_teste.pdf'}

    ids = [doc.metadata['chunk_id'] for doc in documents]
    assert len(ids) == len(set(ids))
    assert all(chunk_id.startswith('chunk_') for chunk_id in ids)

    indexes = [doc.metadata['chunk_index'] for doc in documents]
    assert indexes == list(range(len(documents)))

    pages = {doc.metadata['page'] for doc in documents}
    assert pages == {0, 1}

    last = documents[-1]
    assert last.metadata['chunk_id'] == f"chunk_{len(documents) - 1}"
    assert 'Continuacao do texto na segunda pagina' in last.page_content
    assert last.metadata['page'] == 1


def test_chunks_respect_size_limit_and_rect_bounds(tmp_path):
    pdf_path = tmp_path / 'edital_teste.pdf'
    _create_sample_pdf(str(pdf_path))

    documents = _pdf_to_documents(str(pdf_path))

    for doc in documents:
        assert doc.metadata['page'] in (0, 1)
        assert isinstance(doc.metadata['page'], int)

        rects = doc.metadata['rects']
        assert rects
        for x0, y0, x1, y1 in rects:
            assert 0 <= x0 < x1 <= 612
            assert 0 <= y0 < y1 <= 792

        body = doc.page_content.split('\n\n')[-1]
        assert 0 < len(body) <= MAX_CHARS_PER_CHUNK


def test_section_header_opens_new_prefixed_chunk(tmp_path):
    pdf_path = tmp_path / 'edital_teste.pdf'
    _create_sample_pdf(str(pdf_path))

    documents = _pdf_to_documents(str(pdf_path))

    header_prefix = 'SECTION: 8 - Documentacao de habilitacao'
    section_docs = [
        doc for doc in documents if doc.page_content.startswith(header_prefix)
    ]

    assert section_docs

    assert (
        section_docs[0].metadata['section_title']
        == '8 - Documentacao de habilitacao'
    )

    first_section_body = section_docs[0].page_content.split('\n\n')[-1]
    assert first_section_body.startswith('8 - Documentacao de habilitacao')

    # texto antes do primeiro cabecalho pertence a secao 'Introducao',
    # igual ao comportamento do fluxo antigo (_split_by_sections)
    before_header = [
        doc
        for doc in documents
        if doc.metadata.get('section_title') == 'Introdução'
    ]
    assert before_header
    assert before_header[0].page_content.startswith(
        'SECTION: Introdução\n\n'
    )
    assert 'Linha 0' in before_header[0].page_content

    # contrato exigido por release_logic_service._format_context:
    # todo chunk precisa carregar section_title e o prefixo casar exatamente
    for doc in documents:
        section_title = doc.metadata['section_title']
        assert section_title
        assert doc.page_content.startswith(
            f'SECTION: {section_title}\n\n'
        )
