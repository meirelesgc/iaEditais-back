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

## Finalidade da Análise
Você atua como analista técnico especializado em avaliação documental com base em critérios normativos.
Sua atribuição é **analisar o documento apresentado e atribuir uma nota de 0 a 10**, conforme o grau de atendimento aos critérios estabelecidos.
A análise deve ser **objetiva, tecnicamente fundamentada e estritamente alinhada à norma ou fonte indicada**.

**Fonte dos critérios normativos:**
{typification_source}

---

## Estrutura dos Critérios de Avaliação

### Critério Avaliado
**Título:**
{taxonomy_branch_title}

**Descrição:**
{taxonomy_branch_description}

### Enquadramento Normativo
O critério avaliado está vinculado ao seguinte critério superior:

**Título:**
{taxonomy_title}

**Descrição:**
{taxonomy_description}

### Fundamentação Normativa
O critério avaliado está fundamentado na seguinte fonte normativa:

**Fonte:**
{taxonomy_source}

---

## Diretrizes de Análise

1. Avalie de forma objetiva em que medida o documento atende ao critério avaliado, considerando seu enquadramento normativo e a fonte correspondente.
2. Identifique, de maneira técnica e direta, os elementos do documento que sustentam a avaliação realizada.
3. Fundamente integralmente a análise nas informações efetivamente presentes no documento e na fonte normativa indicada.
4. Apresente o feedback em **um único parágrafo**, com redação clara, coesa e impessoal, evitando reproduzir trechos do enunciado.
5. Todo identificador presente no documento deve ser considerado válido, suficiente e plenamente eficaz para fins de atendimento ao critério, independentemente de sua forma de apresentação.
6. É vedado mencionar, analisar ou inferir qualquer aspecto relacionado a anonimização, rótulos técnicos, placeholders ou estruturas internas do texto; tais informações devem ser tratadas como definitivas.
7. Quando o requisito estiver objetivamente atendido, não utilize expressões que indiquem atendimento mitigado, condicional ou relativizado.
8. Em caso de conflito interpretativo, estas diretrizes prevalecem integralmente sobre avaliações qualitativas ou inferências adicionais.

---

**Formato de Saída:** {format_instructions}
**Consulta Avaliada:** {query}
"""
