from fastapi import APIRouter, UploadFile, File
from iaEditais.services import OrderService
from http import HTTPStatus
from uuid import UUID
from iaEditais.schemas.Order import CreateOrder, Order, Release


router = APIRouter()


@router.post("/order/", status_code=HTTPStatus.CREATED)
def post_order(order: CreateOrder):
    return OrderService.post_order(order)


@router.get("/order/", status_code=HTTPStatus.OK, response_model=list[Order])
def get_orders():
    return OrderService.get_orders()


@router.delete("/order/{order_id}/", status_code=HTTPStatus.NO_CONTENT)
def delete_order(order_id: UUID):
    return OrderService.delete_order(order_id)


@router.get(
    "/order/{order_id}/release/",
    status_code=HTTPStatus.OK,
    response_model=list[Release],
)
def get_releases(order_id: UUID):
    return OrderService.get_releases(order_id)


@router.post(
    "/order/{order_id}/release/",
    status_code=HTTPStatus.CREATED,
    response_model=Release,
)
def post_release(order_id: UUID, file: UploadFile = File(...)):
    return OrderService.post_release(order_id, file)


@router.delete(
    "/order/release/{release_id}/",
    status_code=HTTPStatus.NO_CONTENT,
)
def delete_release(release_id: UUID):
    return OrderService.delete_release(release_id)
