# iaEditais/services/statistics_service.py

from datetime import date, timedelta

import pandas as pd

from iaEditais.core.connection import Connection
from iaEditais.repositories import statistics_repository

# --- 1. Estatísticas Gerais de Uso ---


async def get_general_summary(conn: Connection):
    """
    Service: Repassa a chamada para obter as contagens totais da plataforma.
    Não há necessidade de manipulação de dados aqui.
    """
    return await statistics_repository.get_general_summary(conn)


async def get_analysis_over_time(conn: Connection, days: int):
    """
    Service: Busca dados de análise ao longo do tempo e garante que todos os
    dias no intervalo sejam representados, preenchendo dias sem atividade com zero.
    """
    # 1. Busca os dados brutos do repositório
    raw_data = await statistics_repository.get_analysis_over_time(conn, days)

    if not raw_data:
        return []

    # 2. Converte os dados para um DataFrame do Pandas
    df = pd.DataFrame(raw_data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # 3. Cria um intervalo de datas completo para os últimos 'days' dias
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    # 4. Reindexa o DataFrame para incluir todos os dias, preenchendo os vazios com 0
    df = df.reindex(full_date_range, fill_value=0)
    df['count'] = df['count'].astype(int)

    # 5. Formata o DataFrame de volta para o formato de dicionário para a resposta da API
    df = df.reset_index().rename(columns={'index': 'date'})
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    return df.to_dict('records')


# --- 2. Estatísticas da Base de Conhecimento ---


async def get_typification_usage(conn: Connection):
    """
    Service: Repassa a chamada para obter a contagem de uso de cada tipificação.
    """
    return await statistics_repository.get_typification_usage(conn)


async def get_knowledge_tree_complexity(conn: Connection):
    """
    Service: Repassa a chamada para obter a complexidade das árvores de conhecimento.
    """
    return await statistics_repository.get_knowledge_tree_complexity(conn)


# --- 3. Estatísticas de Atividade e Engajamento ---


async def get_users_per_unit(conn: Connection):
    """
    Service: Repassa a chamada para obter a contagem de usuários por unidade.
    """
    return await statistics_repository.get_users_per_unit(conn)


async def get_activity_by_access_level(conn: Connection):
    """
    Service: Repassa a chamada para obter a contagem de usuários por nível de acesso.
    """
    return await statistics_repository.get_activity_by_access_level(conn)


# --- 4. Estatísticas sobre Fontes Normativas ---


async def get_most_used_sources(conn: Connection):
    """
    Service: Repassa a chamada para obter as fontes normativas mais utilizadas.
    """
    return await statistics_repository.get_most_used_sources(conn)
