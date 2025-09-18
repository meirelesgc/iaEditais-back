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


class DocumentStatus(str, Enum):
    PENDING = 'PENDING'
    UNDER_CONSTRUCTION = 'UNDER_CONSTRUCTION'
    WAITING_FOR_REVIEW = 'WAITING_FOR_REVIEW'
    COMPLETED = 'COMPLETED'


@table_registry.mapped_as_dataclass
class Unit:
    __tablename__ = 'units'

    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(default=None)

    users: Mapped[List['User']] = relationship(
        back_populates='unit',
        default_factory=list,
        init=False,
        foreign_keys='User.unit_id',
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, nullable=True, onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, nullable=True
    )

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_unit_created_by', use_alter=True),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_unit_updated_by', use_alter=True),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_unit_deleted_by', use_alter=True),
        nullable=True,
        default=None,
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
        ForeignKey('units.id', name='fk_user_unit_id'),
        default=None,
        nullable=True,
    )
    unit: Mapped[Optional['Unit']] = relationship(
        back_populates='users', init=False, foreign_keys=[unit_id]
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

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_user_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_user_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_user_deleted_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class TypificationSource:
    __tablename__ = 'typification_sources'

    typification_id: Mapped[UUID] = mapped_column(
        ForeignKey('typifications.id', name='fk_typ_source_typification_id'),
        primary_key=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey('sources.id', name='fk_typ_source_source_id'),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_typ_source_created_by'),
        nullable=True,
        default=None,
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

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_source_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_source_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_source_deleted_by'),
        nullable=True,
        default=None,
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
        lazy='selectin',
    )
    taxonomies: Mapped[List['Taxonomy']] = relationship(
        back_populates='typification',
        default_factory=list,
        init=False,
        lazy='selectin',
    )
    documents: Mapped[List['Document']] = relationship(
        'Document',
        secondary='document_typifications',
        back_populates='typifications',
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

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_typification_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_typification_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_typification_deleted_by'),
        nullable=True,
        default=None,
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
        ForeignKey('typifications.id', name='fk_taxonomy_typification_id'),
        nullable=False,
    )
    typification: Mapped['Typification'] = relationship(
        back_populates='taxonomies', init=False
    )

    branches: Mapped[List['Branch']] = relationship(
        back_populates='taxonomy',
        default_factory=list,
        init=False,
        lazy='selectin',
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

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_taxonomy_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_taxonomy_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_taxonomy_deleted_by'),
        nullable=True,
        default=None,
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
        ForeignKey('taxonomies.id', name='fk_branch_taxonomy_id'),
        nullable=False,
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

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_branch_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_branch_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_branch_deleted_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class DocumentTypification:
    __tablename__ = 'document_typifications'

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey('documents.id', name='fk_doc_typ_document_id'),
        primary_key=True,
    )
    typification_id: Mapped[UUID] = mapped_column(
        ForeignKey('typifications.id', name='fk_doc_typ_typification_id'),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_doc_typ_created_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class Document:
    __tablename__ = 'documents'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )

    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    identifier: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str]

    history: Mapped[List['DocumentHistory']] = relationship(
        back_populates='document',
        init=False,
        default_factory=list,
        order_by='desc(DocumentHistory.created_at)',
    )

    typifications: Mapped[List['Typification']] = relationship(
        'Typification',
        secondary='document_typifications',
        back_populates='documents',
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

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_doc_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_doc_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_doc_deleted_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class DocumentHistory:
    __tablename__ = 'document_histories'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey('documents.id', name='fk_document_histories_document_id'),
        nullable=False,
    )
    document: Mapped['Document'] = relationship(
        back_populates='history', init=False
    )
    status: Mapped[str] = mapped_column(nullable=False)

    messages: Mapped[List['DocumentMessage']] = relationship(
        back_populates='history', cascade='all, delete-orphan', init=False
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
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_histories_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_histories_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_histories_deleted_by'),
        nullable=True,
        default=None,
    )

    releases: Mapped[List['DocumentRelease']] = relationship(
        back_populates='history', cascade='all, delete-orphan', init=False
    )


@table_registry.mapped_as_dataclass
class DocumentRelease:
    __tablename__ = 'document_releases'
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )
    history_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'document_histories.id',
            name='fk_document_releases_history_id',
        ),
        nullable=False,
    )
    history: Mapped['DocumentHistory'] = relationship(
        back_populates='releases', init=False
    )

    file_path: Mapped[str] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, nullable=True
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_releases_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_releases_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_releases_deleted_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class DocumentMessage:
    __tablename__ = 'document_messages'

    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, default=uuid4
    )

    history_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'document_histories.id', name='fk_document_messages_history_id'
        ),
        nullable=False,
    )
    history: Mapped['DocumentHistory'] = relationship(
        back_populates='messages', init=False
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', name='fk_document_messages_user_id'),
        nullable=False,
    )
    user: Mapped['User'] = relationship(init=False, foreign_keys=[user_id])

    message: Mapped[str] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        init=False, nullable=True
    )

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_messages_created_by'),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_messages_updated_by'),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_document_messages_deleted_by'),
        nullable=True,
        default=None,
    )
