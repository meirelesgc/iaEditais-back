from iaEditais.schemas.Order import (
    CreateOrder,
    Order,
    Release,
)


from fastapi import UploadFile
from iaEditais.repositories import (
    OrderRepository,
    TaxonomyRepository,
)
from fastapi import HTTPException

from uuid import UUID


def post_order(order: CreateOrder):
    order = Order(**order.model_dump())
    OrderRepository.post_order(order)
    return order


def get_orders():
    return OrderRepository.get_order()


def get_detailed_orders(order_id: UUID):
    order = OrderRepository.get_order(order_id)
    order['releases'] = OrderRepository.get_releases(order_id)
    return order


def delete_order(order_id: UUID):
    OrderRepository.delete_order(order_id)
    return {'message': 'Order deleted successfully'}


def build_taxonomy(taxonomies: list[UUID] = []):
    if not taxonomies:
        taxonomies = TaxonomyRepository.get_taxonomy()

    taxonomy = taxonomies

    for _, taxonomy in enumerate(taxonomy):
        taxonomy[_]['branches'] = TaxonomyRepository.get_branches(
            taxonomy['id']
        )
    return taxonomy


def post_release(
    order_id: UUID,
    file: UploadFile,
    taxonomies: list[UUID] = [],
):
    taxonomies = [] if not taxonomies else taxonomies

    # Remover depois
    taxonomies = []

    release = Release(
        order_id=order_id,
        taxonomies=taxonomies,
        taxonomy=build_taxonomy(taxonomies),
    )

    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )

    with open(f'storage/releases/{release.id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())

    OrderRepository.post_release(release)

    return release
