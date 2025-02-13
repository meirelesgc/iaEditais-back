from iaEditais.schemas.Order import (
    CreateOrder,
    Order,
    Release,
)
from iaEditais.integrations import OrderIntegrations
from http import HTTPStatus
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
    taxonomies = TaxonomyRepository.get_taxonomy(taxonomies=taxonomies)
    if not taxonomies:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Invalid taxonomy structure.',
        )

    for _, taxonomy in enumerate(taxonomies):
        branch = TaxonomyRepository.get_branches(taxonomy['id'])
        if not branch:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Invalid taxonomy structure.',
            )
        taxonomies[_]['branches'] = branch
    return taxonomies


def post_release(
    order_id: UUID,
    file: UploadFile,
    taxonomies: list[UUID] = [],
) -> Release:
    taxonomies = [] if not taxonomies else taxonomies

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

    release.taxonomy_score = OrderIntegrations.analyze_release(release)

    OrderRepository.post_release(release)
    return release


def get_releases(order_id: UUID) -> list[Release]:
    return OrderRepository.get_releases(order_id)
