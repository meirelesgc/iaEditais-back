# flake8: noqa: E501

DESCRIPTION = """
Gostaria que você elaborasse um resumo geral e sucinto dos pontos avaliados, destacando os melhores e os piores.
Não utilize adjetivos, seja estritamente descritivo.
Sintetize tudo em três ou quatro frases.
\n
"""

ERROR_SUMMARY = """
Elabore um resumo dos pontos que apresentaram problemas.
Não utilize adjetivos, seja estritamente descritivo.
Liste de forma clara e objetiva os seguintes itens:
\n
"""

SUCCESS_SUMMARY = """
Tudo está conforme.
Não utilize adjetivos, seja estritamente descritivo.
Crie um resumo do que foi entendido como aprovado destacando os seguintes pontos:
\n
"""

DOCUMENT_ANALYSIS_PROMPT = """
## Documento para Análise

> {docs}

---

## Sua Missão

Você é um analista especializado em avaliação de documentos segundo regras específicas. Sua tarefa é **verificar se o documento fornecido cumpre os critérios pré-estabelecidos**, fornecendo análises detalhadas para cada item.

**Fonte dos critérios:**
`{typification_source}`

---

## Criteria de Avaliação

### Critério Principal
* **Título:** `{taxonomy_title}`
* **Descrição:** `{taxonomy_description}`
* **Fonte:** `{taxonomy_source}`

### Critério Específico
* **Título:** `{taxonomy_branch_title}`
* **Descrição:** `{taxonomy_branch_description}`

---

## Instruções de Análise

Para cada critério, siga estas instruções rigorosamente:

1.  Identifique se o critério principal e o critério específico estão presentes no documento.
2.  Se o critério específico não estiver contemplado, informe claramente que está ausente.
3.  Avalie a **relevância do critério no contexto geral do documento** (alta, média, baixa) e explique seu raciocínio.
4.  Sugira **melhorias ou ajustes** no documento para atender melhor ao critério.
5.  Cite **a norma, fonte fornecida ou conhecimento implicado** que embasa sua análise.

> **Nota:** Se alguma seção esperada no documento estiver ausente ou não corresponder aos critérios, informe explicitamente.

---

**Formato de Saída:**
`{format_instructions}`

**Consulta:**
`{query}`
"""
