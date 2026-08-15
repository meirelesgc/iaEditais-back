# Carrega e renderiza os templates Jinja2 usados nos prompts de IA da feature.

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PROMPTS_DIR = Path(__file__).resolve().parent / 'prompts'

_environment = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=False,
)


def render_prompt(template_name: str, **context: object) -> str:
    template = _environment.get_template(template_name)
    return template.render(**context)
