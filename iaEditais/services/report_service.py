from datetime import datetime
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


def get_custom_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name='MainTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=12,
            leading=16,
            textColor=colors.black,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            spaceBefore=12,
            spaceAfter=12,
            leading=14,
            textColor=colors.black,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name='TaxonomyTitle',
            parent=styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=11,
            spaceBefore=18,
            spaceAfter=6,
            leading=13,
            textColor=colors.black,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name='ItalicDescription',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            spaceAfter=12,
            leading=12,
            textColor=colors.black,
            alignment=TA_JUSTIFY,
        )
    )

    styles.add(
        ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            spaceAfter=4,
            alignment=TA_JUSTIFY,
        )
    )

    styles.add(
        ParagraphStyle(
            name='BulletItem',
            parent=styles['CustomNormal'],
            leftIndent=15,
            firstLineIndent=0,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        )
    )

    return styles


def draw_horizontal_line(width=16 * cm):
    """
    Cria uma linha horizontal para separação visual.
    """
    d = Drawing(width, 1)
    d.add(Line(0, 0, width, 0, strokeColor=colors.lightgrey, strokeWidth=0.5))
    return d


def create_header_info(typification, styles):
    """
    Gera o cabeçalho com informações do documento.
    """
    elements = []

    elements.append(
        Paragraph(
            'Relatório da Base de Conhecimento: Estudos Técnicos Preliminares (ETP)',
            styles['MainTitle'],
        )
    )

    elements.append(
        Paragraph('Informações do Documento:', styles['SectionHeader'])
    )

    elements.append(
        Paragraph(
            f'<bullet>&bull;</bullet> <b>Nome:</b> {typification.get("name", "-")}',
            styles['BulletItem'],
        )
    )

    created_at = typification.get('created_at', str(datetime.now()))
    if 'T' in str(created_at):
        created_at = str(created_at).split('T')[0]

    elements.append(
        Paragraph(
            f'<bullet>&bull;</bullet> <b>Data de Criação:</b> {created_at}',
            styles['BulletItem'],
        )
    )

    elements.append(Spacer(1, 12))

    elements.append(draw_horizontal_line())
    elements.append(Spacer(1, 12))

    return elements


def create_sources_section(sources, styles):
    """
    Gera a lista de fontes usando parágrafos em vez de tabelas.
    """
    elements = []
    if not sources:
        return elements

    elements.append(Paragraph('Fontes utilizadas:', styles['SectionHeader']))

    for s in sources:
        date_str = str(s.get('created_at', '')).split('T')[0]
        name = s.get('name', 'Sem nome')
        description = s.get('description', '')

        source_text = f'<bullet>&bull;</bullet> <b>{name}</b> ({date_str})'
        elements.append(Paragraph(source_text, styles['BulletItem']))

        if description:
            desc_text = f'<i>Descrição:</i> {description}'

            sub_item_style = ParagraphStyle(
                name='SourceDesc',
                parent=styles['CustomNormal'],
                leftIndent=30,
                alignment=TA_JUSTIFY,
            )
            elements.append(Paragraph(desc_text, sub_item_style))

        elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 6))
    return elements


def create_taxonomy_section(taxonomies, styles):
    """
    Gera a seção de taxonomias e ramos.
    """
    elements = []

    if not taxonomies:
        return elements

    for tax in taxonomies:
        title_text = tax.get('title', 'Sem Título')
        elements.append(Paragraph(title_text, styles['TaxonomyTitle']))

        desc_text = tax.get('description', '')
        if desc_text:
            elements.append(Paragraph(desc_text, styles['ItalicDescription']))

        branches = tax.get('branches', [])
        for b in branches:
            b_title = b.get('title', '')
            b_desc = b.get('description', '')

            full_text = f'<bullet>&bull;</bullet> <b>{b_title}:</b> {b_desc}'

            elements.append(Paragraph(full_text, styles['BulletItem']))

        elements.append(Spacer(1, 6))

    return elements


def typification_report(
    data: dict, output_dir: str = 'iaEditais/storage/temp'
):
    """
    Função principal para geração do PDF.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'iaeditais_report_{today}.pdf'
    filepath = Path(output_dir) / filename

    pdf = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        topMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=3 * cm,
        bottomMargin=3 * cm,
    )

    styles = get_custom_styles()
    content = []

    typifications = data.get('typifications', [])

    for index, tipificacao in enumerate(typifications):
        content.extend(create_header_info(tipificacao, styles))

        if tipificacao.get('sources'):
            content.extend(
                create_sources_section(tipificacao['sources'], styles)
            )

        if tipificacao.get('taxonomies'):
            content.extend(
                create_taxonomy_section(tipificacao['taxonomies'], styles)
            )

        if index < len(typifications) - 1:
            content.append(PageBreak())

    try:
        pdf.build(content)
        return str(filepath)
    except Exception as e:
        print(f'Erro ao gerar PDF: {e}')
        return None


def create_release_header_info(data, styles):
    elements = []

    elements.append(
        Paragraph(
            'Relatório de Avaliação do Edital (Check Tree)',
            styles['MainTitle'],
        )
    )

    elements.append(
        Paragraph('Informações do Documento:', styles['SectionHeader'])
    )

    description = data.get('description')
    if description:
        desc_style = ParagraphStyle(
            name='ReleaseDesc',
            parent=styles['CustomNormal'],
            leftIndent=15,
            alignment=TA_JUSTIFY,
        )
        elements.append(
            Paragraph(f'<b>Descrição:</b> {description}', desc_style)
        )
        elements.append(Spacer(1, 6))

    created_at = data.get('created_at', str(datetime.now()))
    if 'T' in str(created_at):
        created_at = str(created_at).split('T')[0]

    elements.append(
        Paragraph(
            f'<bullet>&bull;</bullet> <b>Criado em:</b> {created_at}',
            styles['BulletItem'],
        )
    )

    elements.append(Spacer(1, 12))
    elements.append(draw_horizontal_line())
    elements.append(Spacer(1, 12))

    return elements


def create_evaluation_item(branch, styles):
    elements = []

    title = branch.get('title', 'Sem título')
    evaluation = branch.get('evaluation') or {}
    fulfilled = evaluation.get('fulfilled')
    score = evaluation.get('score', '-')
    feedback = evaluation.get('feedback', '')

    status = (
        'Cumprido'
        if fulfilled is True
        else 'Não cumprido'
        if fulfilled is False
        else 'Indefinido'
    )

    elements.append(
        Paragraph(
            f'<bullet>&bull;</bullet> <b>{title}</b> — <b>Status:</b> {status} — <b>Nota:</b> {score}',
            styles['BulletItem'],
        )
    )

    if feedback:
        feedback_style = ParagraphStyle(
            name='FeedbackItem',
            parent=styles['CustomNormal'],
            leftIndent=30,
            alignment=TA_JUSTIFY,
        )
        elements.append(
            Paragraph(f'<i>Parecer:</i> {feedback}', feedback_style)
        )

    elements.append(Spacer(1, 6))
    return elements


def create_release_check_tree_section(check_tree, styles):
    elements = []

    if not check_tree:
        return elements

    elements.append(
        Paragraph('Resultados do Check Tree:', styles['SectionHeader'])
    )

    for idx_tip, tip in enumerate(check_tree):
        tip_name = tip.get('name', 'Tipificação sem nome')
        elements.append(Paragraph(tip_name, styles['TaxonomyTitle']))

        tip_sources = tip.get('sources') or []
        if tip_sources:
            elements.extend(create_sources_section(tip_sources, styles))

        taxonomies = tip.get('taxonomies') or []
        for tax in taxonomies:
            title = tax.get('title', 'Sem título')
            description = tax.get('description', '')

            elements.append(Paragraph(title, styles['SectionHeader']))
            if description:
                elements.append(
                    Paragraph(description, styles['ItalicDescription'])
                )

            tax_sources = tax.get('sources') or []
            if tax_sources:
                elements.extend(create_sources_section(tax_sources, styles))

            branches = tax.get('branches') or []
            for b in branches:
                elements.extend(create_evaluation_item(b, styles))

        if idx_tip < len(check_tree) - 1:
            elements.append(PageBreak())

    return elements


def document_release_report(
    data: dict, output_dir: str = 'iaEditais/storage/temp'
):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'iaeditais_document_release_{today}.pdf'
    filepath = Path(output_dir) / filename

    pdf = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        topMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=3 * cm,
        bottomMargin=3 * cm,
    )

    styles = get_custom_styles()
    content = []

    content.extend(create_release_header_info(data, styles))
    content.extend(
        create_release_check_tree_section(data.get('check_tree', []), styles)
    )

    try:
        pdf.build(content)
        return str(filepath)
    except Exception:
        return None
