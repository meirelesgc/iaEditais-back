# Constantes de configuração e tolerâncias da verificação híbrida de template.
# Centralizadas aqui para evitar "magic values" espalhados pelos módulos.

from __future__ import annotations

# Modelo de visão usado na comparação entre template e artigo. gpt-5.4-mini só
# aceita "temperature" quando reasoning.effort='none' (API rejeita a
# combinação com esforço > none); por isso usamos os dois no mínimo.
VISION_MODEL = 'gpt-5.4-mini'
VISION_DPI = 150
VISION_DETAIL = 'high'
VISION_REASONING_EFFORT = 'none'
VISION_TEMPERATURE = 0

# Conversão de unidades (ponto tipográfico -> milímetro).
PT_TO_MM = 25.4 / 72.0

# Tolerâncias de comparação determinística (mesma ordem de grandeza entre critérios).
PAGE_TOL_MM = 5.0
MARGIN_TOL_MM = 17.0
MARGIN_BOTTOM_TOL_MM = 20.0  # margem inferior é mais tolerante: tabelas/rodapés distorcem a bbox.
GUTTER_TOL_MM = 4.0
FONT_SIZE_TOL_PT = 0.7
SPACING_TOL_MM = 35.0

# Identificadores e títulos das 3 seções comparadas (pré-textual, textual, pós-textual).
SEC_PRE = 'elementos_pre_textuais'
SEC_TEXT = 'elementos_textuais'
SEC_POS = 'elementos_pos_textuais'
SEC_TITLES = {
    SEC_PRE: 'Seção de Elementos Pré-Textuais',
    SEC_TEXT: 'Seção de Elementos Textuais',
    SEC_POS: 'Seção de Elementos Pós-Textuais',
}

# Prompt do modelo de visão e pistas usadas para identificar a seção de referências.
VISUAL_PROMPT_TEMPLATE = 'prompt_template.jinja2'
REFERENCES_LABEL_HINTS = ('referências', 'pós-textuais')
