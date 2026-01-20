from .audit_log import AuditLogFilter, AuditLogList, AuditLogPublic
from .branch import (
    BranchCreate,
    BranchFilter,
    BranchList,
    BranchPublic,
    BranchSchema,
    BranchUpdate,
)
from .common import FilterPage, Message, Token, WSMessage
from .document import (
    DocumentCreate,
    DocumentFilter,
    DocumentList,
    DocumentPublic,
    DocumentSchema,
    DocumentUpdate,
)
from .document_history import (
    DocumentHistoryPublic,
    DocumentHistorySchema,
    DocumentStatus,
)
from .document_message import (
    DocumentMessageCreate,
    DocumentMessageList,
    DocumentMessagePublic,
    DocumentMessageUpdate,
    MessageEntityType,
    MessageFilter,
)
from .document_release import (
    AppliedBranchPublic,
    AppliedTaxonomyPublic,
    AppliedTypificationPublic,
    DocumentReleaseFeedback,
    DocumentReleaseList,
    DocumentReleasePublic,
)
from .source import (
    SourceCreate,
    SourceList,
    SourcePublic,
    SourceSchema,
    SourceUpdate,
)
from .taxonomy import (
    TaxonomyCreate,
    TaxonomyList,
    TaxonomyPublic,
    TaxonomySchema,
    TaxonomyUpdate,
)
from .typification import (
    TypificationCreate,
    TypificationList,
    TypificationPublic,
    TypificationSchema,
    TypificationUpdate,
)
from .unit import (
    UnitCreate,
    UnitList,
    UnitPublic,
    UnitSchema,
    UnitUpdate,
)
from .user import (
    AccessType,
    UserCreate,
    UserFilter,
    UserList,
    UserPublic,
    UserPublicMessage,
    UserSchema,
    UserUpdate,
    UserPasswordChange,
)

# 2. Definir explicitamente a API pública do pacote 'schemas'
__all__ = [
    # Módulo branch
    'BranchCreate',
    'BranchFilter',
    'BranchList',
    'BranchPublic',
    'BranchSchema',
    'BranchUpdate',
    # Módulo common
    'FilterPage',
    'Message',
    'Token',
    'WSMessage',
    # Módulo document
    'DocumentCreate',
    'DocumentFilter',
    'DocumentList',
    'DocumentPublic',
    'DocumentSchema',
    'DocumentUpdate',
    # Módulo document_history
    'DocumentHistoryPublic',
    'DocumentHistorySchema',
    'DocumentStatus',
    # Módulo document_message
    'DocumentMessageCreate',
    'DocumentMessagePublic',
    # Módulo document_release
    'AppliedBranchPublic',
    'AppliedTaxonomyPublic',
    'AppliedTypificationPublic',
    'DocumentReleaseFeedback',
    'DocumentReleaseList',
    'DocumentReleasePublic',
    # Módulo source
    'SourceCreate',
    'SourceList',
    'SourcePublic',
    'SourceSchema',
    'SourceUpdate',
    # Módulo taxonomy
    'TaxonomyCreate',
    'TaxonomyList',
    'TaxonomyPublic',
    'TaxonomySchema',
    'TaxonomyUpdate',
    # Módulo typification
    'TypificationCreate',
    'TypificationList',
    'TypificationPublic',
    'TypificationSchema',
    'TypificationUpdate',
    # Módulo unit
    'UnitCreate',
    'UnitList',
    'UnitPublic',
    'UnitSchema',
    'UnitUpdate',
    # Módulo user
    'AccessType',
    'UserCreate',
    'UserFilter',
    'UserList',
    'UserPublic',
    'UserPublicMessage',
    'UserSchema',
    'UserUpdate',
    'UserPasswordChange',
    # Módulo messages
    'DocumentMessageList',
    'DocumentMessageCreate',
    'DocumentMessageUpdate',
    'DocumentMessagePublic',
    'MessageFilter',
    'MessageEntityType',
    # Módulo de logs
    'AuditLogFilter',
    'AuditLogList',
    'AuditLogPublic',
]
