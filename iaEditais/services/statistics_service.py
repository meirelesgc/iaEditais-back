# iaEditais/services/statistics_service.py

from datetime import date, timedelta

import pandas as pd

from iaEditais.core.connection import Connection
from iaEditais.repositories import statistics_repository


async def get_general_summary(conn: Connection):
    return await statistics_repository.get_general_summary(conn)


async def get_analysis_over_time(conn: Connection, days: int):
    raw_data = await statistics_repository.get_analysis_over_time(conn, days)

    if not raw_data:
        return []

    df = pd.DataFrame(raw_data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    df = df.reindex(full_date_range, fill_value=0)
    df['count'] = df['count'].astype(int)

    df = df.reset_index().rename(columns={'index': 'date'})
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    return df.to_dict('records')


async def get_typification_usage(conn: Connection):
    return await statistics_repository.get_typification_usage(conn)


async def get_knowledge_tree_complexity(conn: Connection):
    return await statistics_repository.get_knowledge_tree_complexity(conn)


async def get_users_per_unit(conn: Connection):
    return await statistics_repository.get_users_per_unit(conn)


async def get_activity_by_access_level(conn: Connection):
    return await statistics_repository.get_activity_by_access_level(conn)


async def get_most_used_sources(conn: Connection):
    return await statistics_repository.get_most_used_sources(conn)


async def get_docs_per_unit(conn: Connection):
    return await statistics_repository.get_docs_per_unit(conn)
