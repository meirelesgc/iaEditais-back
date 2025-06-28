from datetime import datetime
from uuid import UUID

from iaEditais.models.branch_model import Branch, CreateBranch
from iaEditais.models.taxonomy_model import CreateTaxonomy, Taxonomy
from iaEditais.repositories import tree_repository


async def post_taxonomy(conn, taxonomy: CreateTaxonomy) -> Taxonomy:
    taxonomy = Taxonomy(**taxonomy.model_dump())
    await tree_repository.post_taxonomy(conn, taxonomy)
    await tree_repository.post_taxonomy_sources(conn, taxonomy)
    return taxonomy


async def get_taxonomy(conn, typification_id: UUID = None) -> list[Taxonomy]:
    return await tree_repository.get_taxonomy(conn, typification_id)


async def put_taxonomy(conn, taxonomy: Taxonomy) -> Taxonomy:
    taxonomy.updated_at = datetime.now()
    await tree_repository.put_taxonomy(conn, taxonomy)
    await tree_repository.delete_taxonomy_sources(conn, taxonomy)
    await tree_repository.post_taxonomy_sources(conn, taxonomy)
    return taxonomy


async def delete_taxonomy(conn, taxonomy_id) -> dict:
    await tree_repository.delete_taxonomy(conn, taxonomy_id)
    return {'message': 'Source deleted successfully'}


async def post_branch(conn, branch: CreateBranch) -> Branch:
    branch = Branch(**branch.model_dump())
    await tree_repository.post_branch(conn, branch)
    return branch


async def get_branches(conn, taxonomy_id: UUID = None) -> list[Branch]:
    return await tree_repository.get_branches(conn, taxonomy_id)


async def put_branch(conn, branch: Branch) -> Branch:
    return await tree_repository.put_branch(conn, branch)


async def delete_branch(conn, branch_id) -> dict:
    await tree_repository.delete_branch(conn, branch_id)
    return {'message': 'Source deleted successfully'}
