# flake8: noqa: E501

DESCRIPTION = """
Receba uma lista de análises, onde cada análise contém:
- feedback (texto)
- nota (número)
- status (contemplado ou não)

Crie um resumo único em um parágrafo pequeno, claro e coeso, que:
- descreva o conteúdo das análises
- inclua informações sobre notas e status de forma concisa
- não repita frases dos feedbacks
- não use adjetivos ou opiniões
- seja estritamente descritivo e objetivo
- não use listas
"""


ERROR_SUMMARY = """
Elabore um resumo dos pontos que apresentaram problemas.
Não utilize adjetivos, seja estritamente descritivo.
Liste de forma clara e objetiva os seguintes itens:
\n
"""

SUCCESS_SUMMARY = """
Elabore um resumo dos pontos contemplados no documento.
Não utilize adjetivos, seja estritamente descritivo.
Liste de forma clara e objetiva os seguintes itens:
\n
"""

DOCUMENT_ANALYSIS_PROMPT = """
## Documento para Análise
> {docs}

---

## Sua Missão
Você é um analista técnico especializado em avaliação documental segundo critérios normativos.  
Sua tarefa é **analisar o documento e atribuir uma nota de 0 a 10** conforme o grau em que o conteúdo atende ao critério apresentado.  
A análise deve ser **coesa, objetiva e fundamentada na norma ou fonte indicada**.

**Fonte dos critérios:** {typification_source}

---

## Critérios de Avaliação

### Critério Principal
* **Título:** {taxonomy_title}
* **Descrição:** {taxonomy_description}
* **Fonte:** {taxonomy_source}

### Critério Específico
* **Título:** {taxonomy_branch_title}
* **Descrição:** {taxonomy_branch_description}

---

## Instruções de Análise

1. Avalie em que medida o documento atende ao critério principal e ao critério específico.
2. Descreva **de forma objetiva e técnica** os pontos fortes e as lacunas observadas.
3. Baseie sua justificativa nas informações do documento e na fonte dos critérios.
4. Escreva o **feedback** em um único parágrafo, claro e coeso, sem repetir frases do enunciado.

---

**Formato de Saída:** {format_instructions}
**Consulta:** {query}
"""
