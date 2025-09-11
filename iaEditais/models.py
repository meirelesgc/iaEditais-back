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
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(default=None)

    users: Mapped[List['User']] = relationship(
        back_populates='unit', default_factory=list, init=False
    )

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
    unit: Mapped[Optional['Unit']] = relationship(
        back_populates='users', init=False
    )

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
class TypificationSource:
    __tablename__ = 'typification_sources'

    typification_id: Mapped[UUID] = mapped_column(
        ForeignKey('typifications.id'), primary_key=True
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey('sources.id'), primary_key=True
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )


@table_registry.mapped_as_dataclass
class Source:
    __tablename__ = 'sources'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )

    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str]

    typifications: Mapped[List['Typification']] = relationship(
        'Typification',
        secondary='typification_sources',
        back_populates='sources',
        default_factory=list,
        init=False,
    )

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
class Typification:
    __tablename__ = 'typifications'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    sources: Mapped[List[Source]] = relationship(
        'Source',
        secondary='typification_sources',
        back_populates='typifications',
        default_factory=list,
        init=False,
    )
    taxonomies: Mapped[List['Taxonomy']] = relationship(
        back_populates='typification', default_factory=list, init=False
    )

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
class Taxonomy:
    __tablename__ = 'taxonomies'

    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )

    title: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str] = mapped_column()

    typification_id: Mapped[UUID] = mapped_column(
        ForeignKey('typifications.id'), nullable=False
    )
    typification: Mapped['Typification'] = relationship(
        back_populates='taxonomies', init=False
    )

    branches: Mapped[List['Branch']] = relationship(
        back_populates='taxonomy', default_factory=list, init=False
    )

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
class Branch:
    __tablename__ = 'branches'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )

    title: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str]

    taxonomy_id: Mapped[UUID] = mapped_column(
        ForeignKey('taxonomies.id'), nullable=False
    )
    taxonomy: Mapped['Taxonomy'] = relationship(
        back_populates='branches', init=False
    )

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
class Doc:
    __tablename__ = 'docs'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )

    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    identifier: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str]

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, nullable=True
    )
