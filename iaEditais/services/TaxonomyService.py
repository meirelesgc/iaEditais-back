from iaEditais.schemas.Taxonomy import Taxonomy, CreateTaxonomy
from uuid import UUID
from datetime import datetime
from iaEditais.schemas.Branch import Branch, CreateBranch
from iaEditais.repositories import TaxonomyRepository


def post_taxonomy(taxonomy: CreateTaxonomy) -> Taxonomy:
    taxonomy = Taxonomy(**taxonomy.model_dump())
    TaxonomyRepository.post_taxonomy(taxonomy)
    return taxonomy


def get_taxonomy() -> list[Taxonomy]:
    taxonomies = TaxonomyRepository.get_taxonomy()
    return taxonomies


def put_taxonomy(taxonomy: Taxonomy) -> Taxonomy:
    taxonomy.updated_at = datetime.now()
    TaxonomyRepository.put_taxonomy(taxonomy)
    return taxonomy


def delete_taxonomy(taxonomy_id) -> dict:
    TaxonomyRepository.delete_taxonomy(taxonomy_id)
    return {'message': 'Source deleted successfully'}


def post_branch(branch: CreateBranch) -> Branch:
    branch = Branch(**branch.model_dump())
    TaxonomyRepository.post_branch(branch)
    return branch


def get_branches(taxonomy_id: UUID = None) -> list[Branch]:
    return TaxonomyRepository.get_branches(taxonomy_id)


def put_branch(branch: Branch) -> Branch:
    return TaxonomyRepository.put_branch(branch)


def delete_branch(branch_id) -> dict:
    TaxonomyRepository.delete_branch(branch_id)
    return {'message': 'Source deleted successfully'}
