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

## Contexto de Localização
Sessão esperada conforme taxonomia: **{expected_session}**

## Finalidade da Análise
Você atua como analista técnico especializado em avaliação documental com base em critérios normativos.
Sua atribuição é **analisar o documento apresentado e atribuir uma nota de 0 a 10**, conforme o grau de atendimento aos critérios estabelecidos.
A análise deve ser **objetiva, tecnicamente fundamentada e estritamente alinhada à norma ou fonte indicada**.

**Fonte dos critérios normativos:**
{typification_source}

---

## Estrutura dos Critérios
### Critério Avaliado
**Título:** {taxonomy_branch_title}
**Descrição:** {taxonomy_branch_description}

### Enquadramento e Fundamentação
**Critério Superior:** {taxonomy_title} ({taxonomy_description})
**Fonte Normativa:** {taxonomy_source}

---

## Diretrizes de Análise

1. Avalie objetivamente o atendimento do documento ao critério avaliado, considerando seu enquadramento normativo e a fonte correspondente, com base exclusivamente nas informações efetivamente presentes no documento.
2. Fundamente a avaliação de forma técnica e direta, identificando os elementos documentais que sustentam a conclusão.
3. O feedback deve ser apresentado em um único parágrafo, com redação clara, coesa e impessoal, sem reproduzir trechos do enunciado.
4. Todo identificador presente no documento deve ser considerado válido, suficiente e plenamente eficaz para fins de atendimento ao critério, independentemente de sua forma de apresentação.
5. É vedado mencionar, analisar ou inferir qualquer aspecto relacionado a anonimização, rótulos técnicos, placeholders ou estruturas internas do texto, devendo tais informações ser tratadas como definitivas.
6. Quando o requisito estiver objetivamente atendido, não utilize expressões que indiquem atendimento mitigado, condicional ou relativizado.
7. Regra de Localização: caso os dados que comprovam o atendimento ao critério estejam em seção diversa da esperada ({expected_session}), a nota atribuída deve ser mantida, devendo-se apenas registrar no feedback que a informação foi localizada em seção divergente.
8. Em caso de conflito interpretativo, estas diretrizes prevalecem integralmente sobre quaisquer avaliações qualitativas adicionais ou inferências não expressamente autorizadas.

---

**Formato de Saída:** {format_instructions}
**Consulta Avaliada:** {query}
"""
