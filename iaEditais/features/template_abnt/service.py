# Orquestração da feature "Conformidade com Template e ABNT": caminhos de
# armazenamento, upload de artigos e disparo/consulta do processamento em
# background (chamado pelos endpoints em iaEditais/routers/template_abnt.py).

from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import BackgroundTasks

from iaEditais.features.template_abnt.abnt_check import abnt as abnt_check
from iaEditais.features.template_abnt.json_store import JsonResultStore
from iaEditais.features.template_abnt.template_check import (
    template as template_check,
)

logger = logging.getLogger(__name__)

FEATURE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = FEATURE_DIR / 'templates'

# Dados gerados em tempo de execução (uploads e resultados) ficam em
# iaEditais/storage, junto com o restante do armazenamento da aplicação.
DATA_DIR = FEATURE_DIR.parent.parent / 'storage' / 'template_abnt'
UPLOADS_DIR = DATA_DIR / 'uploads'
TEMPLATE_RESULTS_DIR = DATA_DIR / 'results' / 'template'
ABNT_RESULTS_DIR = DATA_DIR / 'results' / 'abnt'

for directory in (TEMPLATES_DIR, UPLOADS_DIR, TEMPLATE_RESULTS_DIR, ABNT_RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DEFAULT_TEMPLATE_NAME = 'MDPI Article Template.pdf'
DEFAULT_ARTICLE_FILENAME = 'artigo.pdf'
UPLOAD_PREFIX_TEMPLATE = 'template'
UPLOAD_PREFIX_ABNT = 'abnt'


@lru_cache
def get_template_store() -> JsonResultStore:
    return JsonResultStore(TEMPLATE_RESULTS_DIR)


@lru_cache
def get_abnt_store() -> JsonResultStore:
    return JsonResultStore(ABNT_RESULTS_DIR)


def list_templates() -> list[str]:
    return sorted(p.name for p in TEMPLATES_DIR.glob('*.pdf'))


def resolve_template_path(template_name: str | None) -> Path | None:
    name = template_name or DEFAULT_TEMPLATE_NAME
    path = TEMPLATES_DIR / name
    if path.exists() and path.is_file():
        return path
    return None


def _safe_stem(doc_id: str) -> str:
    return ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in doc_id)


def save_upload(doc_id: str, filename: str, content: bytes, *, prefix: str) -> Path:
    suffix = Path(filename).suffix or '.pdf'
    path = UPLOADS_DIR / f'{prefix}_{_safe_stem(doc_id)}{suffix}'
    path.write_bytes(content)
    return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mark_processing(store: JsonResultStore, doc_id: str) -> None:
    store.save(doc_id, {
        'doc_id': doc_id,
        'status': 'processing',
        'updated_at': _now(),
        'report': None,
        'error': None,
    })


def _mark_completed(store: JsonResultStore, doc_id: str, report: dict) -> None:
    store.save(doc_id, {
        'doc_id': doc_id,
        'status': 'completed',
        'updated_at': _now(),
        'report': report,
        'error': None,
    })


def _mark_error(store: JsonResultStore, doc_id: str, error: str) -> None:
    store.save(doc_id, {
        'doc_id': doc_id,
        'status': 'error',
        'updated_at': _now(),
        'report': None,
        'error': error,
    })


def receive_upload(
    doc_id: str,
    filename: str | None,
    content: bytes,
    *,
    prefix: str,
    store: JsonResultStore,
) -> Path:
    # Salva o PDF recebido e já marca o processamento como "em andamento",
    # reaproveitado pelos dois endpoints POST (template e ABNT).
    article_path = save_upload(doc_id, filename or DEFAULT_ARTICLE_FILENAME, content, prefix=prefix)
    mark_processing(store, doc_id)
    return article_path


async def run_template_analysis(doc_id: str, template_path: Path, article_path: Path) -> None:
    store = get_template_store()
    try:
        report = await template_check.compare(str(template_path), str(article_path))
        _mark_completed(store, doc_id, report.model_dump())
    except Exception as exc:
        logger.exception('Falha na verificação de conformidade com template (doc_id=%s)', doc_id)
        _mark_error(store, doc_id, str(exc))


def run_abnt_analysis(doc_id: str, article_path: Path) -> None:
    store = get_abnt_store()
    try:
        report = abnt_check.compare(str(article_path))
        _mark_completed(store, doc_id, report.model_dump())
    except Exception as exc:
        logger.exception('Falha na verificação de conformidade ABNT (doc_id=%s)', doc_id)
        _mark_error(store, doc_id, str(exc))


def start_template_analysis(
    doc_id: str, filename: str | None, content: bytes,
    template_path: Path, background_tasks: BackgroundTasks,
) -> None:
    store = get_template_store()
    article_path = receive_upload(doc_id, filename, content, prefix=UPLOAD_PREFIX_TEMPLATE, store=store)
    background_tasks.add_task(run_template_analysis, doc_id, template_path, article_path)


def start_abnt_analysis(
    doc_id: str, filename: str | None, content: bytes, background_tasks: BackgroundTasks,
) -> None:
    store = get_abnt_store()
    article_path = receive_upload(doc_id, filename, content, prefix=UPLOAD_PREFIX_ABNT, store=store)
    background_tasks.add_task(run_abnt_analysis, doc_id, article_path)
