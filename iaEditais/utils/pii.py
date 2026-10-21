import re
from typing import List

CPF_PATTERN = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
CNPJ_PATTERN = re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b')
PHONE_PATTERN = re.compile(
    r'\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}\b'
)
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
)
UUID_PATTERN = re.compile(
    r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
    r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'
)


def sanitize_pii(text: str) -> str:
    """Mascara dados pessoais e preserva UUIDs intactos."""
    if not isinstance(text, str):
        return text

    uuids: List[str] = []

    def _replace_uuid(match: re.Match[str]) -> str:
        idx = len(uuids)
        uuids.append(match.group(0))
        return f'__UUID_TOKEN_{idx}__'

    protected_text = UUID_PATTERN.sub(_replace_uuid, text)

    protected_text = CPF_PATTERN.sub('[CPF_MASKED]', protected_text)
    protected_text = CNPJ_PATTERN.sub('[CNPJ_MASKED]', protected_text)
    protected_text = PHONE_PATTERN.sub('[PHONE_MASKED]', protected_text)
    protected_text = EMAIL_PATTERN.sub('[EMAIL_MASKED]', protected_text)

    for idx, original_uuid in enumerate(uuids):
        protected_text = protected_text.replace(
            f'__UUID_TOKEN_{idx}__', original_uuid
        )

    return protected_text
