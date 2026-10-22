"""Sessões de sugestão da árvore de verificação.

Uma sessão nasce com o upload de um PDF, processa o documento em background
e produz itens sugeridos (fonte, tipificação, taxonomias e ramos). Cada item
sofre revisão humana: nada entra na árvore real sem confirmação explícita.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Optional, Sequence
from uuid import UUID, uuid4

import pymupdf
from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.core.database import async_session
from iaEditais.core.dependencies import Storage
from iaEditais.core.settings import Settings
from iaEditais.core.storage_provider import resolve_storage_dir
from iaEditais.features.tree_suggestion.generator import (
    GenerationResult,
    TreeSuggestionGenerationError,
    generate_tree_suggestions,
)
from iaEditais.features.tree_suggestion.structures import (
    ExistingBranch,
    ExistingTaxonomy,
    ExistingTree,
)
from iaEditais.models import (
    Branch,
    DocumentGroup,
    DocumentGroupItem,
    Source,
    Taxonomy,
    TaxonomySource,
    TreeSuggestionItem,
    TreeSuggestionSession,
    Typification,
    TypificationSource,
)
from iaEditais.repositories import tree_suggestion_repo
from iaEditais.schemas import (
    BranchCreate,
    BranchUpdate,
    SourceCreate,
    TaxonomyCreate,
    TaxonomyUpdate,
    TreeSuggestionFilter,
    TreeSuggestionItemConfirm,
    TreeSuggestionItemKind,
    TreeSuggestionItemOperation,
    TreeSuggestionItemStatus,
    TreeSuggestionMode,
    TreeSuggestionSessionDetail,
    TreeSuggestionSessionPublic,
    TreeSuggestionStatus,
    TypificationCreate,
)
from iaEditais.services import (
    branch_service,
    source_service,
    taxonomy_service,
    typification_service,
)
from iaEditais.utils.pii import sanitize_pii

logger = logging.getLogger(__name__)
SETTINGS = Settings()

PDF_CONTENT_TYPES = {'application/pdf', 'application/x-pdf'}
PDF_MAGIC = b'%PDF-'
BYTES_PER_MB = 1024 * 1024
GENERIC_FAILURE = 'Falha inesperada ao gerar as sugestões.'
TIMEOUT_FAILURE = 'Tempo limite de processamento excedido.'


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=HTTPStatus.CONFLICT, detail=detail)


def _local_path(file_path: str) -> Path:
    return resolve_storage_dir(SETTINGS.UPLOAD_DIRECTORY) / os.path.basename(
        file_path
    )


# --- Criação ---------------------------------------------------------------


def _count_pdf_pages(content: bytes) -> int:
    try:
        with pymupdf.open(stream=content, filetype='pdf') as pdf:
            return pdf.page_count
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail='Invalid PDF file',
        ) from exc


async def _validate_upload(file: UploadFile) -> int:
    content = await file.read()
    await file.seek(0)

    if file.content_type not in PDF_CONTENT_TYPES or not content.startswith(
        PDF_MAGIC
    ):
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail='Only PDF files are supported',
        )

    if len(content) > SETTINGS.TREE_SUGGESTION_MAX_FILE_MB * BYTES_PER_MB:
        raise HTTPException(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            detail='File exceeds the maximum size',
        )

    page_count = _count_pdf_pages(content)
    if page_count > SETTINGS.TREE_SUGGESTION_MAX_PAGES:
        raise HTTPException(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            detail='File exceeds the maximum number of pages',
        )
    return page_count


async def _get_active_typification(
    session: AsyncSession, typification_id: UUID
) -> Typification:
    typification = await session.get(Typification, typification_id)
    if not typification or typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )
    return typification


async def _validate_document_group(
    session: AsyncSession,
    document_group_id: Optional[UUID],
    document_group_item_id: Optional[UUID],
) -> tuple[Optional[UUID], Optional[UUID]]:
    """Valida o grupo e o tipo de documento informados na criação da sessão."""
    if not document_group_id and not document_group_item_id:
        return None, None

    if not document_group_id:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail='Document group is required',
        )

    group = await session.get(DocumentGroup, document_group_id)
    if not group or group.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group not found',
        )

    if not document_group_item_id:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail='Document group item is required',
        )

    item = await session.get(DocumentGroupItem, document_group_item_id)
    if not item or item.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group item not found',
        )

    if item.group_id != group.id:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail='Document group item does not belong to the group',
        )

    return group.id, item.id


async def create_session(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    user_id: UUID,
    storage: Storage,
    file: UploadFile,
    typification_id: Optional[UUID] = None,
    background_tasks: Optional[BackgroundTasks] = None,
    document_group_id: Optional[UUID] = None,
    document_group_item_id: Optional[UUID] = None,
) -> TreeSuggestionSessionDetail:
    page_count = await _validate_upload(file)
    if typification_id:
        await _get_active_typification(session, typification_id)

    group_id, group_item_id = await _validate_document_group(
        session, document_group_id, document_group_item_id
    )

    unique_filename = f'{uuid4()}_{os.path.basename(file.filename or "")}'
    file_path = await storage.save(file, unique_filename)

    suggestion = TreeSuggestionSession(
        mode=(
            TreeSuggestionMode.ENRICH.value
            if typification_id
            else TreeSuggestionMode.CREATE.value
        ),
        file_path=file_path,
        original_filename=file.filename or unique_filename,
        target_typification_id=typification_id,
        document_group_id=group_id,
        document_group_item_id=group_item_id,
        page_count=page_count,
        processing_started_at=_utcnow(),
    )
    suggestion.set_creation_audit(user_id)
    tree_suggestion_repo.add_session(session, suggestion)
    await session.commit()

    if background_tasks is not None:
        background_tasks.add_task(
            run_tree_suggestion_background, suggestion.id
        )

    return await get_session_detail(session, suggestion.id)


# --- Processamento em background -------------------------------------------


async def _load_existing_tree(
    session: AsyncSession, suggestion: TreeSuggestionSession
) -> ExistingTree:
    names = await session.execute(
        select(Typification.id, Typification.name).where(
            Typification.deleted_at.is_(None)
        )
    )
    existing = ExistingTree(typification_names=[tuple(r) for r in names])
    if not suggestion.target_typification_id:
        return existing

    typification = await _get_active_typification(
        session, suggestion.target_typification_id
    )
    existing.typification_id = typification.id
    existing.typification_name = typification.name
    taxonomies = await session.scalars(
        select(Taxonomy)
        .options(selectinload(Taxonomy.branches))
        .where(
            Taxonomy.typification_id == typification.id,
            Taxonomy.deleted_at.is_(None),
        )
        .order_by(Taxonomy.created_at)
        .execution_options(populate_existing=True)
    )
    existing.taxonomies = [
        ExistingTaxonomy(
            id=taxonomy.id,
            title=taxonomy.title,
            description=taxonomy.description,
            branches=[
                ExistingBranch(
                    id=branch.id,
                    title=branch.title,
                    description=branch.description,
                )
                for branch in taxonomy.branches
                if branch.deleted_at is None
            ],
        )
        for taxonomy in taxonomies
    ]
    return existing


async def _source_names(session: AsyncSession):
    rows = await session.execute(
        select(Source.id, Source.name).where(Source.deleted_at.is_(None))
    )
    return [tuple(r) for r in rows]


def _snapshot(entity) -> dict:
    return {
        'title': entity.title,
        'description': entity.description,
        'updated_at': (
            entity.updated_at.isoformat() if entity.updated_at else None
        ),
    }


async def _build_items(
    session: AsyncSession,
    suggestion: TreeSuggestionSession,
    result: GenerationResult,
) -> list[TreeSuggestionItem]:
    items: list[TreeSuggestionItem] = []
    ids_by_key: dict[str, UUID] = {}
    for position, node in enumerate(result.nodes):
        snapshot = None
        if node.operation == TreeSuggestionItemOperation.UPDATE.value:
            model = Taxonomy if node.kind == 'taxonomy' else Branch
            entity = await session.get(
                model, node.target_entity_id, populate_existing=True
            )
            if not entity or entity.deleted_at:
                continue
            snapshot = _snapshot(entity)

        if node.parent_key and node.parent_key not in ids_by_key:
            continue

        item = TreeSuggestionItem(
            session_id=suggestion.id,
            kind=node.kind,
            operation=node.operation,
            proposed_title=node.title,
            proposed_description=node.description,
            position=position,
            parent_item_id=ids_by_key.get(node.parent_key),
            parent_entity_id=node.parent_entity_id,
            target_entity_id=node.target_entity_id,
            target_snapshot=snapshot,
            evidence=node.evidence,
            rationale=node.rationale,
            similar_to_id=node.similar_to_id,
            similarity_note=node.similarity_note,
        )
        ids_by_key[node.key] = item.id
        items.append(item)
    return items


async def _run_generation(
    session: AsyncSession, suggestion: TreeSuggestionSession
) -> None:
    existing = await _load_existing_tree(session, suggestion)
    result = await generate_tree_suggestions(
        str(_local_path(suggestion.file_path)),
        suggestion.mode,
        existing,
        source_names=await _source_names(session),
    )
    items = await _build_items(session, suggestion, result)
    tree_suggestion_repo.add_items(session, items)
    suggestion.status = TreeSuggestionStatus.READY.value
    suggestion.page_count = result.page_count
    suggestion.generation_model = result.model_name
    suggestion.excluded_rules = result.excluded_rules
    suggestion.processing_finished_at = _utcnow()
    await session.commit()


async def _generate_items(session: AsyncSession, suggestion_id: UUID) -> None:
    suggestion = await tree_suggestion_repo.get_session(session, suggestion_id)
    if (
        not suggestion
        or suggestion.status != TreeSuggestionStatus.PROCESSING.value
    ):
        return

    try:
        await _run_generation(session, suggestion)
    except Exception as exc:
        await session.rollback()
        message = (
            str(exc)
            if isinstance(exc, (TreeSuggestionGenerationError, HTTPException))
            else GENERIC_FAILURE
        )
        if isinstance(exc, HTTPException):
            message = str(exc.detail)
        logger.exception(
            'Falha ao gerar sugestões da sessão %s', suggestion_id
        )
        await _mark_failed(session, suggestion_id, message)


async def _mark_failed(
    session: AsyncSession, suggestion_id: UUID, message: str
) -> None:
    suggestion = await tree_suggestion_repo.get_session(session, suggestion_id)
    if not suggestion:
        return
    suggestion.status = TreeSuggestionStatus.FAILED.value
    suggestion.error_message = sanitize_pii(message)
    suggestion.processing_finished_at = _utcnow()
    await session.commit()


async def run_tree_suggestion_background(suggestion_id: UUID) -> None:
    """Gera os itens da sessão numa sessão de banco própria."""
    try:
        async with async_session() as session:
            await _generate_items(session, suggestion_id)
    except Exception:
        logger.exception(
            'Erro inesperado no processamento da sessão %s', suggestion_id
        )


# --- Leitura ---------------------------------------------------------------


async def _expire_if_stale(
    session: AsyncSession, suggestion: TreeSuggestionSession
) -> bool:
    limit = timedelta(
        minutes=SETTINGS.TREE_SUGGESTION_PROCESSING_TIMEOUT_MINUTES
    )
    started = suggestion.processing_started_at or suggestion.created_at
    if (
        suggestion.status == TreeSuggestionStatus.PROCESSING.value
        and started
        and _utcnow() - started > limit
    ):
        suggestion.status = TreeSuggestionStatus.FAILED.value
        suggestion.error_message = TIMEOUT_FAILURE
        suggestion.processing_finished_at = _utcnow()
        return True
    return False


async def _get_suggestion(
    session: AsyncSession, suggestion_id: UUID
) -> TreeSuggestionSession:
    suggestion = await tree_suggestion_repo.get_session(session, suggestion_id)
    if not suggestion:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Suggestion session not found',
        )
    if await _expire_if_stale(session, suggestion):
        await session.commit()
    return suggestion


async def _entity_titles(
    session: AsyncSession, model, ids: Sequence[UUID]
) -> dict[UUID, str]:
    if not ids:
        return {}
    column = model.name if model is Typification else model.title
    rows = await session.execute(
        select(model.id, column).where(model.id.in_(set(ids)))
    )
    return {row[0]: row[1] for row in rows}


async def _document_group_names(
    session: AsyncSession, suggestion: TreeSuggestionSession
) -> tuple[Optional[str], Optional[str]]:
    group_name = None
    item_name = None

    if suggestion.document_group_id:
        group = await session.get(DocumentGroup, suggestion.document_group_id)
        group_name = group.name if group else None

    if suggestion.document_group_item_id:
        item = await session.get(
            DocumentGroupItem, suggestion.document_group_item_id
        )
        item_name = item.name if item else None

    return group_name, item_name


async def _to_public_sessions(
    session: AsyncSession, suggestions: Sequence[TreeSuggestionSession]
) -> list[TreeSuggestionSessionPublic]:
    """Serializa as sessões da listagem com os nomes das referências."""
    public_list = [
        TreeSuggestionSessionPublic.model_validate(suggestion)
        for suggestion in suggestions
    ]

    typification_ids = {
        suggestion.target_typification_id
        for suggestion in suggestions
        if suggestion.target_typification_id
    }
    group_ids = {
        suggestion.document_group_id
        for suggestion in suggestions
        if suggestion.document_group_id
    }
    item_ids = {
        suggestion.document_group_item_id
        for suggestion in suggestions
        if suggestion.document_group_item_id
    }

    typification_titles = await _entity_titles(
        session, Typification, list(typification_ids)
    )
    group_names: dict[UUID, str] = {}
    if group_ids:
        rows = await session.execute(
            select(DocumentGroup.id, DocumentGroup.name).where(
                DocumentGroup.id.in_(group_ids)
            )
        )
        group_names = {row[0]: row[1] for row in rows}
    item_names: dict[UUID, str] = {}
    if item_ids:
        rows = await session.execute(
            select(DocumentGroupItem.id, DocumentGroupItem.name).where(
                DocumentGroupItem.id.in_(item_ids)
            )
        )
        item_names = {row[0]: row[1] for row in rows}

    for public in public_list:
        if public.target_typification_id:
            public.target_typification_name = typification_titles.get(
                public.target_typification_id
            )
        if public.document_group_id:
            public.document_group_name = group_names.get(
                public.document_group_id
            )
        if public.document_group_item_id:
            public.document_group_item_name = item_names.get(
                public.document_group_item_id
            )

    return public_list


async def _to_detail(
    session: AsyncSession, suggestion: TreeSuggestionSession
) -> TreeSuggestionSessionDetail:
    detail = TreeSuggestionSessionDetail.model_validate(suggestion)

    def parent_ids(kind: str):
        return [
            i.parent_entity_id
            for i in detail.items
            if i.kind == kind and i.parent_entity_id
        ]

    typification_ids = parent_ids('taxonomy')
    if detail.target_typification_id:
        typification_ids.append(detail.target_typification_id)
    typification_titles = await _entity_titles(
        session, Typification, typification_ids
    )
    taxonomy_titles = await _entity_titles(
        session, Taxonomy, parent_ids('branch')
    )

    detail.target_typification_name = typification_titles.get(
        detail.target_typification_id
    )
    (
        detail.document_group_name,
        detail.document_group_item_name,
    ) = await _document_group_names(session, suggestion)
    for item in detail.items:
        titles = (
            typification_titles if item.kind == 'taxonomy' else taxonomy_titles
        )
        item.parent_entity_title = titles.get(item.parent_entity_id)
    return detail


async def get_session_detail(
    session: AsyncSession, suggestion_id: UUID
) -> TreeSuggestionSessionDetail:
    suggestion = await _get_suggestion(session, suggestion_id)
    return await _to_detail(session, suggestion)


async def list_sessions(
    session: AsyncSession, filters: TreeSuggestionFilter
) -> list[TreeSuggestionSessionPublic]:
    sessions = list(await tree_suggestion_repo.list_sessions(session, filters))
    expired = [s for s in sessions if await _expire_if_stale(session, s)]
    if expired:
        await session.commit()
    if filters.status:
        sessions = [s for s in sessions if s.status == filters.status.value]
    return await _to_public_sessions(session, sessions)


# --- Revisão ---------------------------------------------------------------


async def _get_reviewable(
    session: AsyncSession, suggestion_id: UUID
) -> TreeSuggestionSession:
    suggestion = await _get_suggestion(session, suggestion_id)
    if suggestion.status != TreeSuggestionStatus.READY.value:
        raise _conflict('Suggestion session is not ready for review')
    return suggestion


async def _get_pending_item(
    session: AsyncSession, suggestion_id: UUID, item_id: UUID
) -> TreeSuggestionItem:
    item = await tree_suggestion_repo.get_item_for_update(
        session, suggestion_id, item_id
    )
    if not item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Suggestion item not found',
        )
    if item.status != TreeSuggestionItemStatus.PENDING.value:
        raise _conflict('Suggestion item is not pending')
    return item


async def _complete_if_done(
    session: AsyncSession, suggestion: TreeSuggestionSession
) -> None:
    await session.flush()
    if not await tree_suggestion_repo.count_pending(session, suggestion.id):
        suggestion.status = TreeSuggestionStatus.COMPLETED.value


async def _resolve_parent(session: AsyncSession, item: TreeSuggestionItem):
    if item.parent_item_id:
        parent = await tree_suggestion_repo.get_item(
            session, item.parent_item_id
        )
        if (
            not parent
            or parent.status != TreeSuggestionItemStatus.CONFIRMED.value
        ):
            raise _conflict('Parent item must be confirmed first')
        return parent.applied_entity_id

    model = Typification if item.kind == 'taxonomy' else Taxonomy
    parent = await session.get(model, item.parent_entity_id)
    if not parent or parent.deleted_at:
        raise _conflict('Parent entity no longer exists')
    return parent.id


async def _session_source_id(
    session: AsyncSession, suggestion_id: UUID
) -> Optional[UUID]:
    confirmed = await tree_suggestion_repo.list_confirmed(
        session, suggestion_id, [TreeSuggestionItemKind.SOURCE.value]
    )
    return confirmed[0].applied_entity_id if confirmed else None


async def _link_source(
    session: AsyncSession,
    user_id: UUID,
    source_id: UUID,
    typification_ids: Sequence[UUID] = (),
    taxonomy_ids: Sequence[UUID] = (),
) -> None:
    for typification_id in set(typification_ids):
        if not await session.get(
            TypificationSource, (typification_id, source_id)
        ):
            session.add(
                TypificationSource(
                    typification_id=typification_id,
                    source_id=source_id,
                    created_by=user_id,
                )
            )
    for taxonomy_id in set(taxonomy_ids):
        if not await session.get(TaxonomySource, (taxonomy_id, source_id)):
            session.add(
                TaxonomySource(
                    taxonomy_id=taxonomy_id,
                    source_id=source_id,
                    created_by=user_id,
                )
            )


def _check_snapshot(item: TreeSuggestionItem, entity) -> None:
    if (
        not entity
        or entity.deleted_at
        or _snapshot(entity) != (item.target_snapshot or {})
    ):
        raise _conflict('Target entity changed since the suggestion')


async def _apply_source(
    session, user_id, suggestion, title, description
) -> UUID:
    source = await source_service.create_source(
        session,
        user_id,
        SourceCreate(name=title, description=description),
        commit=False,
    )
    source.file_path = suggestion.file_path

    applied = await tree_suggestion_repo.list_confirmed(
        session,
        suggestion.id,
        [
            TreeSuggestionItemKind.TYPIFICATION.value,
            TreeSuggestionItemKind.TAXONOMY.value,
        ],
    )
    typification_ids = [
        i.applied_entity_id for i in applied if i.kind == 'typification'
    ]
    if suggestion.target_typification_id:
        typification_ids.append(suggestion.target_typification_id)
    await _link_source(
        session,
        user_id,
        source.id,
        typification_ids,
        [i.applied_entity_id for i in applied if i.kind == 'taxonomy'],
    )
    return source.id


async def _apply_item(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    user_id: UUID,
    suggestion: TreeSuggestionSession,
    item: TreeSuggestionItem,
    title: str,
    description: str,
) -> UUID:
    if item.kind == TreeSuggestionItemKind.SOURCE.value:
        return await _apply_source(
            session, user_id, suggestion, title, description
        )

    source_id = await _session_source_id(session, suggestion.id)
    source_ids = [source_id] if source_id else []
    is_update = item.operation == TreeSuggestionItemOperation.UPDATE.value

    if item.kind == TreeSuggestionItemKind.TYPIFICATION.value:
        entity = await typification_service.create_typification(
            session,
            user_id,
            TypificationCreate(
                name=title,
                source_ids=source_ids,
                document_group_id=suggestion.document_group_id,
                document_group_item_id=suggestion.document_group_item_id,
            ),
            commit=False,
        )
    elif item.kind == TreeSuggestionItemKind.TAXONOMY.value and is_update:
        current = await session.scalar(
            select(Taxonomy)
            .options(selectinload(Taxonomy.sources))
            .where(Taxonomy.id == item.target_entity_id)
            .execution_options(populate_existing=True)
        )
        _check_snapshot(item, current)
        entity = await taxonomy_service.update_taxonomy(
            session,
            user_id,
            TaxonomyUpdate(
                id=current.id,
                title=title,
                description=description,
                typification_id=current.typification_id,
                source_ids=list(
                    {s.id for s in current.sources} | set(source_ids)
                ),
            ),
            commit=False,
        )
    elif item.kind == TreeSuggestionItemKind.TAXONOMY.value:
        entity = await taxonomy_service.create_taxonomy(
            session,
            user_id,
            TaxonomyCreate(
                title=title,
                description=description,
                typification_id=await _resolve_parent(session, item),
                source_ids=source_ids,
            ),
            commit=False,
        )
    elif is_update:
        current = await session.get(
            Branch, item.target_entity_id, populate_existing=True
        )
        _check_snapshot(item, current)
        entity = await branch_service.update_branch(
            session,
            user_id,
            BranchUpdate(
                id=current.id,
                title=title,
                description=description,
                taxonomy_id=current.taxonomy_id,
            ),
            commit=False,
        )
    else:
        entity = await branch_service.create_branch(
            session,
            user_id,
            BranchCreate(
                title=title,
                description=description,
                taxonomy_id=await _resolve_parent(session, item),
            ),
            commit=False,
        )
    return entity.id


async def confirm_item(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    user_id: UUID,
    suggestion_id: UUID,
    item_id: UUID,
    data: Optional[TreeSuggestionItemConfirm] = None,
) -> TreeSuggestionItem:
    data = data or TreeSuggestionItemConfirm()
    suggestion = await _get_reviewable(session, suggestion_id)
    item = await _get_pending_item(session, suggestion_id, item_id)

    title = (data.title or item.proposed_title).strip()
    description = (
        data.description
        if data.description is not None
        else item.proposed_description
    ) or ''

    try:
        applied_id = await _apply_item(
            session, user_id, suggestion, item, title, description
        )
    except HTTPException:
        await session.rollback()
        raise

    item.status = TreeSuggestionItemStatus.CONFIRMED.value
    item.final_title = title
    item.final_description = description
    item.applied_entity_id = applied_id
    item.reviewed_by = user_id
    item.reviewed_at = _utcnow()
    await _complete_if_done(session, suggestion)
    await session.commit()

    return item


async def discard_item(
    session: AsyncSession,
    user_id: UUID,
    suggestion_id: UUID,
    item_id: UUID,
) -> TreeSuggestionSessionDetail:
    suggestion = await _get_reviewable(session, suggestion_id)
    item = await _get_pending_item(session, suggestion_id, item_id)

    descendants = await tree_suggestion_repo.list_pending_descendant_ids(
        session, item.id
    )
    await tree_suggestion_repo.mark_discarded(
        session, [item.id, *descendants], user_id, _utcnow()
    )
    await _complete_if_done(session, suggestion)
    await session.commit()
    return await get_session_detail(session, suggestion_id)


async def discard_session(
    session: AsyncSession, user_id: UUID, suggestion_id: UUID
) -> TreeSuggestionSessionDetail:
    suggestion = await _get_reviewable(session, suggestion_id)
    pending = await tree_suggestion_repo.list_pending_ids(
        session, suggestion.id
    )
    await tree_suggestion_repo.mark_discarded(
        session, pending, user_id, _utcnow()
    )
    suggestion.status = TreeSuggestionStatus.COMPLETED.value
    await session.commit()
    return await get_session_detail(session, suggestion_id)
