from iaEditais.schemas.taxonomy import Taxonomy, CreateTaxonomy
from uuid import UUID
from datetime import datetime
from iaEditais.schemas.branch import Branch, CreateBranch
from iaEditais.repositories import taxonomy_repository


def post_taxonomy(taxonomy: CreateTaxonomy) -> Taxonomy:
    taxonomy = Taxonomy(**taxonomy.model_dump())
    taxonomy_repository.post_taxonomy(taxonomy)
    return taxonomy


def get_taxonomy(typification_id: UUID = None) -> list[Taxonomy]:
    taxonomies = taxonomy_repository.get_taxonomy(typification_id)
    return taxonomies


def put_taxonomy(taxonomy: Taxonomy) -> Taxonomy:
    taxonomy.updated_at = datetime.now()
    taxonomy_repository.put_taxonomy(taxonomy)
    return taxonomy


def delete_taxonomy(taxonomy_id) -> dict:
    taxonomy_repository.delete_taxonomy(taxonomy_id)
    return {'message': 'Source deleted successfully'}


def post_branch(branch: CreateBranch) -> Branch:
    branch = Branch(**branch.model_dump())
    taxonomy_repository.post_branch(branch)
    return branch


def get_branches(taxonomy_id: UUID = None) -> list[Branch]:
    return taxonomy_repository.get_branches(taxonomy_id)


def put_branch(branch: Branch) -> Branch:
    return taxonomy_repository.put_branch(branch)


def delete_branch(branch_id) -> dict:
    taxonomy_repository.delete_branch(branch_id)
    return {'message': 'Source deleted successfully'}
