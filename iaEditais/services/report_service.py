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
    filename = f'relatorio_tipificacoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    filepath = Path(output_dir) / filename

    pdf = SimpleDocTemplate(str(filepath), pagesize=A4)
    estilos = getSampleStyleSheet()
    conteudo = [
        Paragraph('Relatório de Tipificações', estilos['Title']),
        Spacer(1, 12),
    ]

    for t in data.get('typifications', []):
        conteudo.append(
            Paragraph(f'<b>Nome:</b> {t["name"]}', estilos['Heading2'])
        )
        conteudo.append(Spacer(1, 6))

        # Fontes
        if t.get('sources'):
            conteudo.append(Paragraph('<b>Fontes:</b>', estilos['Heading3']))
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
            conteudo.append(tabela)
            conteudo.append(Spacer(1, 12))

        # Taxonomias
        if t.get('taxonomies'):
            conteudo.append(
                Paragraph('<b>Taxonomias:</b>', estilos['Heading3'])
            )
            for tax in t['taxonomies']:
                conteudo.append(
                    Paragraph(f'<u>{tax["title"]}</u>', estilos['Heading4'])
                )
                conteudo.append(
                    Paragraph(tax['description'], estilos['Normal'])
                )
                conteudo.append(Spacer(1, 6))

                if tax.get('branches'):
                    conteudo.append(
                        Paragraph('<b>Ramos:</b>', estilos['Heading4'])
                    )
                    for b in tax['branches']:
                        conteudo.append(
                            Paragraph(f'• {b["title"]}', estilos['Normal'])
                        )
                        conteudo.append(
                            Paragraph(b['description'], estilos['Normal'])
                        )
                        conteudo.append(Spacer(1, 4))

                conteudo.append(Spacer(1, 12))

        conteudo.append(Spacer(1, 24))

    pdf.build(conteudo)
    return str(filepath)
