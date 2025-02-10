from fastapi import APIRouter, UploadFile, File, Form
from iaEditais.services import OrderService
from http import HTTPStatus
from uuid import UUID
from iaEditais.schemas.Order import CreateOrder, Order


router = APIRouter()


@router.post('/order/', status_code=HTTPStatus.CREATED)
def post_order(order: CreateOrder):
    return OrderService.post_order(order)


@router.get('/order/', status_code=HTTPStatus.OK, response_model=list[Order])
def get_orders():
    return OrderService.get_orders()


@router.get('/order/{order_id}/', status_code=HTTPStatus.OK)
def get_detailed_orders(order_id: UUID):
    return OrderService.get_detailed_orders(order_id)


@router.delete('/order/{order_id}', status_code=HTTPStatus.NO_CONTENT)
def delete_order(order_id: UUID):
    return OrderService.delete_order(order_id)


@router.post('/order/release/', status_code=HTTPStatus.CREATED)
def post_release(
    order_id: UUID = Form(...),
    taxonomies: list[UUID] = Form(None),
    file: UploadFile = File(...),
):
    return OrderService.post_release(order_id, file, taxonomies)
