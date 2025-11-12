from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def typification_report(
    data: dict, output_dir: str = 'iaEditais/storage/temp'
):
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'iaeditais_report_{today}.pdf'
    filepath = Path(output_dir) / filename

    pdf = SimpleDocTemplate(str(filepath), pagesize=A4)
    style = getSampleStyleSheet()
    content = [
        Paragraph('Relatório da base de conhecimento', style['Title']),
        Spacer(1, 12),
    ]

    for t in data.get('typifications', []):
        content.append(
            Paragraph(f'<b>Nome:</b> {t["name"]}', style['Heading2'])
        )
        content.append(Spacer(1, 6))

        if t.get('sources'):
            content.append(Paragraph('<b>Fontes:</b>', style['Heading3']))
            tabela_fontes = [['Nome', 'Descrição', 'Criado em']]
            for s in t['sources']:
                tabela_fontes.append([
                    s['name'],
                    s['description'],
                    s['created_at'].split('T')[0],
                ])
            tabela = Table(tabela_fontes)
            tabela.setStyle(
                TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ])
            )
            content.append(tabela)
            content.append(Spacer(1, 12))

        if t.get('taxonomies'):
            content.append(Paragraph('<b>Taxonomias:</b>', style['Heading3']))
            for tax in t['taxonomies']:
                content.append(
                    Paragraph(f'<u>{tax["title"]}</u>', style['Heading4'])
                )
                content.append(Paragraph(tax['description'], style['Normal']))
                content.append(Spacer(1, 6))

                if tax.get('branches'):
                    content.append(
                        Paragraph('<b>Ramos:</b>', style['Heading4'])
                    )
                    for b in tax['branches']:
                        content.append(
                            Paragraph(f'• {b["title"]}', style['Normal'])
                        )
                        content.append(
                            Paragraph(b['description'], style['Normal'])
                        )
                        content.append(Spacer(1, 4))

                content.append(Spacer(1, 12))

        content.append(Spacer(1, 24))

    pdf.build(content)
    return str(filepath)
