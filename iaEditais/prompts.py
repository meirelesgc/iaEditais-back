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
Sua atribuição é **avaliar o documento apresentado e atribuir uma nota final de 0 a 10**, exclusivamente com base no barema definido abaixo.
A análise deve ser **objetiva, tecnicamente fundamentada e estritamente aderente à norma ou fonte indicada**.

**Fonte dos critérios normativos:**
{typification_source}

---

## Estrutura do Critério Avaliado
**Título:** {taxonomy_branch_title}
**Descrição:** {taxonomy_branch_description}

**Critério Superior:** {taxonomy_title} ({taxonomy_description})
**Fonte Normativa:** {taxonomy_source}

---

## Barema de Avaliação (0 a 10)

A nota final deve ser a soma direta dos pontos atribuídos a cada item, sem arredondamentos ou ajustes subjetivos.

1. Enquadramento na Sessão Esperada - até 3 pontos
Avalia se as informações que comprovam o atendimento ao critério estão localizadas na sessão esperada ({expected_session}).

2. Aderência ao Critério Normativo Avaliado - até 3 pontos
Avalia o grau de conformidade objetiva do conteúdo com o critério normativo e sua fonte.

3. Clareza e Objetividade das Informações - até 2 pontos
Avalia se as informações são claras, diretas e suficientes para compreensão técnica, sem ambiguidades.

4. Suficiência dos Elementos Documentais - até 2 pontos
Avalia se os elementos presentes no documento são suficientes para comprovar o atendimento ao critério.

---

## Diretrizes de Análise

1. A avaliação deve considerar exclusivamente as informações efetivamente presentes no documento.
2. Todo identificador presente deve ser considerado válido, suficiente e plenamente eficaz.
3. É vedado mencionar ou inferir qualquer aspecto relacionado a anonimização, placeholders ou estruturas internas.
4. Caso as informações estejam em seção diversa da esperada, aplique a penalização correspondente no item de localização e registre essa condição no feedback.
5. Quando o requisito estiver atendido, não utilize linguagem mitigadora ou condicional.
6. Em caso de conflito interpretativo, estas diretrizes prevalecem sobre qualquer inferência adicional.

---

## Saída Esperada

- Nota final de 0 a 10
- Pontuação detalhada por item do barema
- Feedback técnico em **um único parágrafo**, claro, impessoal e fundamentado

**Formato de Saída:** {format_instructions}
**Consulta Avaliada:** {query}
"""
