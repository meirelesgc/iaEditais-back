from datetime import datetime
from typing import Optional
from uuid import UUID

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.dependencies import Model, VStore
from iaEditais.models import (
    AppliedBranch,
    AppliedSource,
    AppliedTaxonomy,
    AppliedTypification,
    DocumentRelease,
)
from iaEditais.repositories import release_repo
from iaEditais.schemas.common import WSMessage
from iaEditais.schemas.document_release import DocumentReleasePublic
from iaEditais.services import (
    release_logic_service,
    tree_service,
    vector_service,
)


# --- WebSocket Helper ---
async def _ws_update(redis: Redis, db_release: DocumentRelease, message: str):
    release_public = DocumentReleasePublic.model_validate(db_release)
    payload = release_public.model_dump(mode='json')
    ws_message = WSMessage(
        event='doc.release.update',
        message=message,
        payload=payload,
    )
    await redis.publish('ws:broadcast', ws_message.model_dump_json())


# --- Persistence Helpers ---
async def _save_eval_results(
    session: AsyncSession,
    eval_args: list[dict],
    release_id: UUID,
    user_id: Optional[UUID] = None,
):
    applied_typs: dict[UUID, AppliedTypification] = {}
    applied_taxes: dict[UUID, AppliedTaxonomy] = {}

    for branch_data in eval_args:
        branch_id = branch_data.get('id')
        if not branch_id:
            continue

        original_branch = await release_repo.get_full_branch(
            session, branch_id
        )
        if not original_branch:
            continue

        # Hierarquia
        tax = original_branch.taxonomy
        typ = tax.typification

        # Applied Typification
        app_typ = applied_typs.get(typ.id)
        if not app_typ:
            app_typ = await release_repo.get_applied_typification(
                session, typ.id, release_id
            )
            if not app_typ:
                app_typ = AppliedTypification(
                    name=typ.name,
                    applied_release_id=release_id,
                    original_id=typ.id,
                    created_by=user_id,
                )
                for src in typ.sources:
                    app_typ.sources.append(
                        AppliedSource(
                            name=src.name,
                            description=src.description,
                            original_id=src.id,
                            created_by=user_id,
                        )
                    )
                release_repo.add_applied_entity(session, app_typ)
                await session.flush()
            applied_typs[typ.id] = app_typ

        # Applied Taxonomy
        app_tax = applied_taxes.get(tax.id)
        if not app_tax:
            app_tax = await release_repo.get_applied_taxonomy(
                session, tax.id, app_typ.id
            )
            if not app_tax:
                app_tax = AppliedTaxonomy(
                    title=tax.title,
                    description=tax.description,
                    applied_typification_id=app_typ.id,
                    original_id=tax.id,
                    created_by=user_id,
                )
                for src in tax.sources:
                    app_tax.sources.append(
                        AppliedSource(
                            name=src.name,
                            description=src.description,
                            original_id=src.id,
                            created_by=user_id,
                        )
                    )
                release_repo.add_applied_entity(session, app_tax)
                await session.flush()
            applied_taxes[tax.id] = app_tax

        # Applied Branch
        applied_branch = AppliedBranch(
            title=original_branch.title,
            description=original_branch.description,
            applied_taxonomy_id=app_tax.id,
            original_id=original_branch.id,
            created_by=user_id,
            fulfilled=branch_data.get('fulfilled'),
            score=branch_data.get('score'),
            feedback=branch_data.get('feedback'),
            presidio_mapping=str(branch_data.get('presidio_mapping')),
        )
        release_repo.add_applied_entity(session, applied_branch)

    await session.flush()


async def process_release_pipeline(
    session: AsyncSession,
    release_id: UUID,
    model: Model,
    vstore: VStore,
    redis: Redis,
) -> dict:
    db_release = await release_repo.get_release_with_details(
        session, release_id
    )
    if not db_release:
        raise ValueError(f'DocumentRelease {release_id} not found.')

    db_doc = db_release.history.document

    try:
        await _ws_update(redis, db_release, 'creating_vectors')
        await vector_service.create_vectors(db_release.file_path, vstore)

        await _ws_update(redis, db_release, 'evaluating')
        tree = await tree_service.get_tree_by_release(session, db_release)

        args = await release_logic_service.get_eval_args(
            vstore, tree, db_release
        )
        simplified_args = await release_logic_service.simplify_eval_args(args)

        chain = release_logic_service.get_chain(model)
        await release_logic_service.apply_tree(chain, simplified_args)

        await _save_eval_results(session, simplified_args, db_release.id)

        prompt = release_logic_service.generate_description_prompt(
            simplified_args
        )
        desc_response = model.invoke(prompt)
        db_release.description = desc_response.content.strip()
        await session.commit()

        await _ws_update(redis, db_release, 'complete')

        log_path = f'iaEditais/storage/temp/{datetime.now().isoformat()}.py'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f'eval_args = {repr(simplified_args)}')

        return {'doc': db_doc, 'release': db_release, 'status': 'success'}

    except Exception as e:
        raise e
