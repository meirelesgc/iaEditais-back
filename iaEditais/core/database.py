from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from iaEditais.core.settings import Settings
from iaEditais.models import AuditMixin

settings = Settings()

engine = create_async_engine(settings.DATABASE_URL, future=True)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@event.listens_for(Session, 'do_orm_execute')
def _add_filtering_criteria(execute_state: ORMExecuteState):
    skip_filter = execute_state.execution_options.get(
        'skip_soft_delete_filter', False
    )
    if execute_state.is_select and not skip_filter:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                AuditMixin,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
        )


async def get_session():
    async with async_session() as session:
        yield session
