from iaEditais.schemas.Order import (
    CreateOrder,
    Order,
    Release,
)
import os
from fastapi.responses import FileResponse
from fastapi import UploadFile
from iaEditais.repositories import OrderRepository, TaxonomyRepository
from iaEditais.integrations import Integrations
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


def build_taxonomy(order_id: UUID):
    taxonomy = TaxonomyRepository.get_typification(order_id=order_id)
    for typification in taxonomy:
        typification_id = typification.get('id')
        typification['taxonomy'] = TaxonomyRepository.get_taxonomy(
            typification_id
        )
        for item in typification['taxonomy']:
            item_id = item.get('id')
            item['branch'] = TaxonomyRepository.get_branches(item_id)
    return taxonomy


def post_release(
    order_id: UUID,
    file: UploadFile,
) -> Release:
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )
    release = Release(order_id=order_id, taxonomy=build_taxonomy(order_id))

    with open(f'storage/releases/{release.id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())
    Integrations.add_to_vector_store(f'storage/releases/{release.id}.pdf')
    release = Integrations.analyze_release(release)
    OrderRepository.post_release(release)
    return release


def get_releases(order_id: UUID) -> list[Release]:
    return OrderRepository.get_releases(order_id)


def delete_release(release_id: UUID):
    OrderRepository.delete_release(release_id)


def get_release_file(release_id: UUID = None):
    file_path = f'storage/releases/{release_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(file_path)
