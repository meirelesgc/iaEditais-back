from fastapi import APIRouter, Depends

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.services import statistics_service

router = APIRouter(prefix='/statistics', tags=['Statistics'])


@router.get('/general-summary')
async def get_general_summary(conn: Connection = Depends(get_conn)):
    return await statistics_service.get_general_summary(conn)


@router.get('/analysis-over-time')
async def get_analysis_over_time(
    conn: Connection = Depends(get_conn), days: int = 30
):
    return await statistics_service.get_analysis_over_time(conn, days)


@router.get('/typification-usage')
async def get_typification_usage(conn: Connection = Depends(get_conn)):
    return await statistics_service.get_typification_usage(conn)


@router.get('/knowledge-tree-complexity')
async def get_knowledge_tree_complexity(conn: Connection = Depends(get_conn)):
    return await statistics_service.get_knowledge_tree_complexity(conn)


@router.get('/users-per-unit')
async def get_users_per_unit(conn: Connection = Depends(get_conn)):
    return await statistics_service.get_users_per_unit(conn)


@router.get('/activity-by-access-level')
async def get_activity_by_access_level(conn: Connection = Depends(get_conn)):
    return await statistics_service.get_activity_by_access_level(conn)


@router.get('/most-used-sources')
async def get_most_used_sources(conn: Connection = Depends(get_conn)):
    return await statistics_service.get_most_used_sources(conn)


@router.get('/get_docs_per_unit')
async def get_docs_per_unit(conn: Connection = Depends(get_conn)):
    return await statistics_service.get_docs_per_unit(conn)
