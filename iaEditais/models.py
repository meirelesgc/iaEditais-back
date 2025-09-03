from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

table_registry = registry()


class AccessType(str, Enum):
    DEFAULT = 'DEFAULT'
    ADMIN = 'ADMIN'
    ANALYST = 'ANALYST'
    AUDITOR = 'AUDITOR'


@table_registry.mapped_as_dataclass
class Unit:
    __tablename__ = 'units'

    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(unique=True)
    location: Mapped[Optional[str]] = mapped_column(default=None)

    # --- Relacionamento ---
    users: Mapped[List['User']] = relationship(
        back_populates='unit', default_factory=list, init=False
    )

    # --- Campos de Auditoria ---
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        init=False, nullable=True, onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        init=False, nullable=True
    )


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )
    username: Mapped[str]
    phone_number: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    access_level: Mapped[str] = mapped_column(default=AccessType.DEFAULT)
    unit_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('units.id'), default=None, nullable=True
    )
    # --- Relacionamento ---
    unit: Mapped[Optional['Unit']] = relationship(
        back_populates='users', init=False
    )

    # --- Campos de Auditoria (para consistência) ---
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, nullable=True
    )


@table_registry.mapped_as_dataclass
class Source:
    __tablename__ = 'sources'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]

    # --- Campos de Auditoria (para consistência) ---
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, nullable=True
    )
