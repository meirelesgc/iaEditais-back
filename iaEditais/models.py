from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, column, func
from sqlalchemy.orm import (
    Mapped,
    declared_attr,
    mapped_column,
    registry,
    relationship,
)

from iaEditais.schemas import AccessType

table_registry = registry()


@dataclass(init=False)
class AuditMixin:
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(init=False, server_default=func.now())

    @declared_attr
    def updated_at(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(init=False, nullable=True, onupdate=func.now())

    @declared_attr
    def deleted_at(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(init=False, nullable=True)

    @declared_attr
    def created_by(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey(
                'users.id',
                name=f'fk_{cls.__tablename__}_created_by',
                use_alter=True,
            ),
            nullable=True,
            default=None,
        )

    @declared_attr
    def updated_by(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey(
                'users.id',
                name=f'fk_{cls.__tablename__}_updated_by',
                use_alter=True,
            ),
            nullable=True,
            default=None,
        )

    @declared_attr
    def deleted_by(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey(
                'users.id',
                name=f'fk_{cls.__tablename__}_deleted_by',
                use_alter=True,
            ),
            nullable=True,
            default=None,
        )

    def set_creation_audit(self, user_id: UUID):
        self.created_at = func.now()
        self.created_by = user_id

    def set_update_audit(self, user_id: UUID):
        self.updated_at = func.now()
        self.updated_by = user_id

    def set_deletion_audit(self, user_id: UUID):
        self.deleted_at = func.now()
        self.deleted_by = user_id


@table_registry.mapped_as_dataclass
class Unit(AuditMixin):
    __tablename__ = 'units'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    location: Mapped[Optional[str]] = mapped_column(default=None)

    users: Mapped[List['User']] = relationship(
        back_populates='unit',
        default_factory=list,
        init=False,
        foreign_keys='User.unit_id',
        lazy='selectin',
    )
    documents: Mapped[List['Document']] = relationship(
        back_populates='unit',
        default_factory=list,
        init=False,
        foreign_keys='Document.unit_id',
        lazy='selectin',
    )

    __table_args__ = (
        Index(
            'ix_uq_units_name_active',
            'name',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class User(AuditMixin):
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    username: Mapped[str]
    phone_number: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column()
    password: Mapped[str]
    access_level: Mapped[str] = mapped_column(default=AccessType.DEFAULT)

    unit_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('units.id', name='fk_user_unit_id'),
        default=None,
        nullable=True,
    )
    icon_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('user_images.id', name='fk_users_icon_id'),
        default=None,
        nullable=True,
    )
    icon: Mapped[Optional['UserImage']] = relationship(
        foreign_keys=[icon_id], init=False, lazy='selectin'
    )
    unit: Mapped[Optional['Unit']] = relationship(
        back_populates='users', init=False, foreign_keys=[unit_id]
    )

    editable_documents: Mapped[List['Document']] = relationship(
        'Document',
        lazy='selectin',
        secondary='document_editors',
        primaryjoin='User.id==DocumentEditor.user_id',
        secondaryjoin='Document.id==DocumentEditor.document_id',
        back_populates='editors',
        default_factory=list,
        init=False,
    )

    __table_args__ = (
        Index(
            'ix_uq_users_phone_number_active',
            'phone_number',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
        Index(
            'ix_uq_users_email_active',
            'email',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
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
class Source(AuditMixin):
    __tablename__ = 'sources'
    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str]
    file_path: Mapped[str] = mapped_column(nullable=True, init=False)
    typifications: Mapped[List['Typification']] = relationship(
        'Typification',
        lazy='noload',
        secondary='typification_sources',
        back_populates='sources',
        default_factory=list,
        init=False,
    )
    taxonomies: Mapped[List['Taxonomy']] = relationship(
        'Taxonomy',
        lazy='noload',
        secondary='taxonomy_sources',
        back_populates='sources',
        default_factory=list,
        init=False,
    )

    __table_args__ = (
        Index(
            'ix_uq_sources_name_active',
            'name',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class Typification(AuditMixin):
    __tablename__ = 'typifications'
    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    name: Mapped[str] = mapped_column(nullable=False)

    sources: Mapped[List[Source]] = relationship(
        'Source',
        lazy='selectin',
        secondary='typification_sources',
        back_populates='typifications',
        default_factory=list,
        init=False,
    )
    taxonomies: Mapped[List['Taxonomy']] = relationship(
        back_populates='typification',
        lazy='selectin',
        default_factory=list,
        init=False,
    )
    documents: Mapped[List['Document']] = relationship(
        'Document',
        lazy='selectin',
        secondary='document_typifications',
        back_populates='typifications',
        default_factory=list,
        init=False,
    )

    __table_args__ = (
        Index(
            'ix_uq_typifications_name_active',
            'name',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class TaxonomySource:
    __tablename__ = 'taxonomy_sources'

    taxonomy_id: Mapped[UUID] = mapped_column(
        ForeignKey('taxonomies.id', name='fk_tax_source_taxonomy_id'),
        primary_key=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey('sources.id', name='fk_tax_source_source_id'),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_tax_source_created_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class Taxonomy(AuditMixin):
    __tablename__ = 'taxonomies'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    title: Mapped[str] = mapped_column(nullable=False)
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
        lazy='selectin',
        default_factory=list,
        init=False,
    )
    sources: Mapped[List['Source']] = relationship(
        'Source',
        lazy='selectin',
        secondary='taxonomy_sources',
        back_populates='taxonomies',
        default_factory=list,
        init=False,
    )

    __table_args__ = (
        Index(
            'ix_uq_taxonomies_title_active',
            'title',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class Branch(AuditMixin):
    __tablename__ = 'branches'
    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str]

    taxonomy_id: Mapped[UUID] = mapped_column(
        ForeignKey('taxonomies.id', name='fk_branch_taxonomy_id'),
        nullable=False,
    )
    taxonomy: Mapped['Taxonomy'] = relationship(
        back_populates='branches', init=False
    )

    __table_args__ = (
        Index(
            'ix_uq_branch_title_active',
            'title',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
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
class DocumentEditor:
    __tablename__ = 'document_editors'

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey('documents.id', name='fk_doc_editor_document_id'),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', name='fk_doc_editor_user_id'),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    granted_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_doc_editor_granted_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class Document(AuditMixin):
    __tablename__ = 'documents'
    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    name: Mapped[str] = mapped_column(nullable=False)
    identifier: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str]

    unit_id: Mapped[UUID] = mapped_column(
        ForeignKey('units.id'), nullable=False
    )
    unit: Mapped['Unit'] = relationship(
        back_populates='documents',
        lazy='selectin',
        init=False,
    )

    history: Mapped[List['DocumentHistory']] = relationship(
        back_populates='document',
        lazy='selectin',
        init=False,
        default_factory=list,
        order_by='desc(DocumentHistory.created_at)',
    )

    typifications: Mapped[List['Typification']] = relationship(
        'Typification',
        lazy='selectin',
        secondary='document_typifications',
        back_populates='documents',
        default_factory=list,
        init=False,
    )

    editors: Mapped[List['User']] = relationship(
        'User',
        lazy='selectin',
        secondary='document_editors',
        primaryjoin='Document.id==DocumentEditor.document_id',
        secondaryjoin='User.id==DocumentEditor.user_id',
        back_populates='editable_documents',
        default_factory=list,
        init=False,
    )
    messages: Mapped[List['DocumentMessage']] = relationship(
        'DocumentMessage',
        back_populates='document',
        lazy='selectin',
        default_factory=list,
        init=False,
        cascade='all, delete-orphan',
    )

    is_test: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index(
            'ix_uq_documents_name_active',
            'name',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
        Index(
            'ix_uq_documents_identifier_active',
            'identifier',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class DocumentHistory(AuditMixin):
    __tablename__ = 'document_histories'
    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey('documents.id', name='fk_document_histories_document_id'),
        nullable=False,
    )
    document: Mapped['Document'] = relationship(
        back_populates='history', init=False
    )
    status: Mapped[str] = mapped_column(nullable=False)

    releases: Mapped[List['DocumentRelease']] = relationship(
        back_populates='history',
        cascade='all, delete-orphan',
        init=False,
        lazy='noload',
    )


@table_registry.mapped_as_dataclass
class DocumentRelease(AuditMixin):
    __tablename__ = 'document_releases'
    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
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

    check_tree: Mapped[List['AppliedTypification']] = relationship(
        'AppliedTypification',
        lazy='selectin',
        back_populates='release',
        default_factory=list,
        init=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        nullable=True, default=None
    )

    messages: Mapped[List['DocumentMessage']] = relationship(
        'DocumentMessage',
        back_populates='release',
        lazy='selectin',
        default_factory=list,
        init=False,
        cascade='all, delete-orphan',
    )

    is_test: Mapped[bool] = mapped_column(default=False)


@table_registry.mapped_as_dataclass
class AppliedSource:
    __tablename__ = 'applied_sources'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    name: Mapped[str] = mapped_column(unique=False, nullable=False)

    typifications: Mapped[List['AppliedTypification']] = relationship(
        secondary='applied_typification_sources',
        lazy='selectin',
        back_populates='sources',
        default_factory=list,
        init=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    applied_taxonomies: Mapped[List['AppliedTaxonomy']] = relationship(
        'AppliedTaxonomy',
        lazy='selectin',
        secondary='applied_taxonomy_sources',
        back_populates='sources',
        default_factory=list,
        init=False,
    )
    original_id: Mapped[Optional[UUID]] = mapped_column(
        nullable=True,
        default=None,
    )
    description: Mapped[Optional[str]] = mapped_column(
        nullable=True, default=None
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class AppliedTypificationSource:
    __tablename__ = 'applied_typification_sources'

    typification_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'applied_typifications.id',
            name='fk_applied_typ_source_typification_id',
        ),
        primary_key=True,
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'applied_sources.id', name='fk_applied_typ_source_source_id'
        ),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_applied_typ_source_created_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class AppliedTypification:
    __tablename__ = 'applied_typifications'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    name: Mapped[str] = mapped_column(nullable=False)

    applied_release_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'document_releases.id',
            name='fk_applied_typification_release_id',
        ),
        nullable=False,
    )

    release: Mapped['DocumentRelease'] = relationship(
        back_populates='check_tree', init=False
    )

    original_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(
            'typifications.id',
            name='fk_applied_typification_original_id',
        ),
        nullable=True,
        default=None,
    )

    taxonomies: Mapped[List['AppliedTaxonomy']] = relationship(
        back_populates='typification',
        lazy='selectin',
        default_factory=list,
        init=False,
    )

    sources: Mapped[List[AppliedSource]] = relationship(
        'AppliedSource',
        lazy='selectin',
        secondary='applied_typification_sources',
        back_populates='typifications',
        default_factory=list,
        init=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_applied_typification_created_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class AppliedTaxonomySource:
    __tablename__ = 'applied_taxonomy_sources'

    taxonomy_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'applied_taxonomies.id',
            name='fk_applied_tax_source_taxonomy_id',
        ),
        primary_key=True,
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'applied_sources.id', name='fk_applied_tax_source_source_id'
        ),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_applied_tax_source_created_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class AppliedTaxonomy:
    __tablename__ = 'applied_taxonomies'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    title: Mapped[str] = mapped_column(nullable=False)
    applied_typification_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'applied_typifications.id',
            name='fk_applied_taxonomy_typification_id',
        ),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        nullable=True, default=None
    )
    original_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('taxonomies.id', name='fk_applied_taxonomy_original_id'),
        nullable=True,
        default=None,
    )

    typification: Mapped['AppliedTypification'] = relationship(
        back_populates='taxonomies', init=False
    )
    branches: Mapped[List['AppliedBranch']] = relationship(
        back_populates='taxonomy',
        lazy='selectin',
        default_factory=list,
        init=False,
    )
    sources: Mapped[List['AppliedSource']] = relationship(
        'AppliedSource',
        lazy='selectin',
        secondary='applied_taxonomy_sources',
        back_populates='applied_taxonomies',
        default_factory=list,
        init=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_applied_taxonomy_created_by'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class AppliedBranch:
    __tablename__ = 'applied_branches'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    title: Mapped[str] = mapped_column(nullable=False)

    applied_taxonomy_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'applied_taxonomies.id', name='fk_applied_branch_taxonomy_id'
        ),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        nullable=True, default=None
    )

    taxonomy: Mapped['AppliedTaxonomy'] = relationship(
        back_populates='branches', init=False
    )

    original_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('branches.id', name='fk_applied_branch_original_id'),
        nullable=True,
        default=None,
    )

    feedback: Mapped[Optional[str]] = mapped_column(
        nullable=True, default=None
    )
    fulfilled: Mapped[Optional[bool]] = mapped_column(
        nullable=True, default=None
    )
    score: Mapped[Optional[int]] = mapped_column(nullable=True, default=None)

    presidio_mapping: Mapped[Optional[str]] = mapped_column(
        nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('users.id', name='fk_applied_branch_created_by'),
        nullable=True,
        default=None,
    )

    @property
    def evaluation(self) -> dict:
        return {
            'feedback': self.feedback,
            'fulfilled': self.fulfilled,
            'score': self.score,
        }


@table_registry.mapped_as_dataclass
class DocumentMessage(AuditMixin):
    __tablename__ = 'document_messages'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    content: Mapped[str] = mapped_column(nullable=False)

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey('documents.id', name='fk_doc_msg_document_id'),
        nullable=False,
    )
    document: Mapped['Document'] = relationship(
        back_populates='messages', init=False
    )

    release_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('document_releases.id', name='fk_doc_msg_release_id'),
        nullable=True,
    )
    release: Mapped[Optional['DocumentRelease']] = relationship(
        back_populates='messages', init=False
    )

    author_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', name='fk_doc_msg_author_id'),
        nullable=False,
    )
    author: Mapped['User'] = relationship(
        init=False,
        lazy='selectin',
        foreign_keys=[author_id],
    )
    quoted_message_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(
            'document_messages.id', name='fk_doc_msg_quoted_message_id'
        ),
        nullable=True,
        default=None,
    )
    quoted_message: Mapped[Optional['DocumentMessage']] = relationship(
        remote_side='DocumentMessage.id', init=False, lazy='selectin'
    )

    mentions: Mapped[List['DocumentMessageMention']] = relationship(
        back_populates='message',
        lazy='selectin',
        cascade='all, delete-orphan',
        init=False,
        default_factory=list,
    )

    __table_args__ = (
        Index(
            'ix_doc_msg_document_id_created_at',
            'document_id',
            'created_at',
        ),
    )


@table_registry.mapped_as_dataclass
class DocumentMessageMention:
    __tablename__ = 'document_message_mentions'
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'document_messages.id', name='fk_doc_msg_mention_message_id'
        ),
        primary_key=True,
    )
    entity_id: Mapped[UUID] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(nullable=False)
    label: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)

    message: Mapped['DocumentMessage'] = relationship(
        back_populates='mentions', init=False
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )


@table_registry.mapped_as_dataclass
class UserImage:
    __tablename__ = 'user_images'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    type: Mapped[str] = mapped_column(nullable=False)
    file_path: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )


# ===========================
# Evaluation Models
# ===========================


@table_registry.mapped_as_dataclass
class TestCollection(AuditMixin):
    """Agrupador de casos de teste."""

    __tablename__ = 'test_collections'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(default=None)

    __table_args__ = (
        Index(
            'ix_uq_test_collections_name_active',
            'name',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class AIModel(AuditMixin):
    """Modelos de IA usados nas métricas."""

    __tablename__ = 'ai_models'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    code_name: Mapped[str] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            'ix_uq_ai_models_code_name_active',
            'code_name',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class Metric(AuditMixin):
    """Critérios de avaliação."""

    __tablename__ = 'metrics'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    criteria: Mapped[Optional[str]] = mapped_column(default=None)
    evaluation_steps: Mapped[Optional[str]] = mapped_column(default=None)
    threshold: Mapped[Optional[float]] = mapped_column(default=0.5)


@table_registry.mapped_as_dataclass
class TestCase(AuditMixin):
    """Cenários de teste."""

    __tablename__ = 'test_cases'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    test_collection_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'test_collections.id', name='fk_test_cases_test_collection_id'
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    doc_id: Mapped[UUID] = mapped_column(
        ForeignKey('documents.id', name='fk_test_cases_doc_id'),
        nullable=False,
    )
    branch_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('branches.id', name='fk_test_cases_branch_id'),
        nullable=True,
        default=None,
    )
    input: Mapped[Optional[str]] = mapped_column(default=None)
    expected_feedback: Mapped[Optional[str]] = mapped_column(default=None)
    expected_fulfilled: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index(
            'ix_uq_test_cases_name_collection_doc_active',
            'name',
            'test_collection_id',
            'doc_id',
            unique=True,
            postgresql_where=(column('deleted_at').is_(None)),
        ),
    )


@table_registry.mapped_as_dataclass
class TestRun(AuditMixin):
    """Evento de execução de testes."""

    __tablename__ = 'test_runs'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )
    test_collection_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(
            'test_collections.id', name='fk_test_runs_test_collection_id'
        ),
        nullable=True,
        default=None,
    )
    test_case_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('test_cases.id', name='fk_test_runs_test_case_id'),
        nullable=True,
        default=None,
    )
    status: Mapped[str] = mapped_column(default='pending')
    progress: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    error_message: Mapped[Optional[str]] = mapped_column(
        nullable=True, default=None
    )
    release_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('document_releases.id', name='fk_test_runs_release_id'),
        nullable=True,
        default=None,
    )


@table_registry.mapped_as_dataclass
class TestResult(AuditMixin):
    """Resultados detalhados dos testes."""

    __tablename__ = 'test_results'

    id: Mapped[UUID] = mapped_column(
        init=False,
        primary_key=True,
        insert_default=uuid4,
        default_factory=uuid4,
    )

    test_run_id: Mapped[UUID] = mapped_column(
        ForeignKey('test_runs.id', name='fk_test_results_test_run_id'),
        nullable=False,
    )
    test_case_id: Mapped[UUID] = mapped_column(
        ForeignKey('test_cases.id', name='fk_test_results_test_case_id'),
        nullable=False,
    )
    metric_id: Mapped[UUID] = mapped_column(
        ForeignKey('metrics.id', name='fk_test_results_metric_id'),
        nullable=False,
    )
    model_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('ai_models.id', name='fk_test_results_model_id'),
        nullable=True,
        default=None,
    )

    threshold_used: Mapped[Optional[float]] = mapped_column(default=None)
    reason_feedback: Mapped[Optional[str]] = mapped_column(default=None)
    score_feedback: Mapped[Optional[float]] = mapped_column(default=None)
    passed_feedback: Mapped[Optional[bool]] = mapped_column(default=None)
    actual_feedback: Mapped[Optional[str]] = mapped_column(default=None)
    actual_fulfilled: Mapped[Optional[bool]] = mapped_column(default=None)
    passed_fulfilled: Mapped[Optional[bool]] = mapped_column(default=None)

    test_case: Mapped['TestCase'] = relationship(
        'TestCase', lazy='selectin', init=False
    )