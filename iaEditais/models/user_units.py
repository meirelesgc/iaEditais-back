from uuid import UUID

from pydantic import BaseModel


class CreateUserUnit(BaseModel):
    user_id: UUID
    unit_id: UUID


class UserUnit(CreateUserUnit):
    pass


class DeleteUserUnit(CreateUserUnit):
    pass
