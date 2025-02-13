from iaEditais.schemas.Typification import CreateTypification, Typification
from datetime import datetime
from uuid import UUID
from iaEditais.repositories import TypificationRepository


def post_typification(typification: CreateTypification) -> Typification:
    typification = Typification(**typification.model_dump())
    TypificationRepository.post_typification(typification)
    return typification


def get_typification(
    typification_id: UUID = None,
) -> list[Typification] | Typification:
    return TypificationRepository.get_typification(typification_id)


def get_detailed_typification(type_id) -> list[Typification] | Typification:
    return TypificationRepository.get_typification(type_id)


def put_typification(typification: Typification):
    typification.updated_at = datetime.now()
    TypificationRepository.put_typification(typification)
    return typification


def delete_typification(typification_id: UUID):
    TypificationRepository.delete_typification(typification_id)
    return {'message': 'Typificação deletada com sucesso.'}
