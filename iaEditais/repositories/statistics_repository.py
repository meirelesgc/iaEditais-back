from iaEditais.core.connection import Connection


async def get_general_summary(conn: Connection):
    SCRIPT_SQL = """
        SELECT
            (SELECT COUNT(*) FROM units) AS total_units,
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM docs WHERE deleted_at IS NULL) AS total_docs,
            (SELECT COUNT(*) FROM releases WHERE deleted_at IS NULL) AS total_releases,
            (SELECT COUNT(*) FROM typifications WHERE deleted_at IS NULL) AS total_typifications;
    """
    return await conn.select(SCRIPT_SQL, one=True)


async def get_analysis_over_time(conn: Connection, days: int):
    params = {'days': days}

    SCRIPT_SQL = """
        SELECT
            DATE(created_at) AS date,
            COUNT(id) AS count
        FROM releases
        WHERE created_at >= CURRENT_DATE - (%(days)s || ' days')::interval
        GROUP BY DATE(created_at)
        ORDER BY date ASC;
    """
    return await conn.select(SCRIPT_SQL, params)


async def get_typification_usage(conn: Connection):
    SCRIPT_SQL = """
        SELECT
            t.name,
            COUNT(dt.doc_id) AS doc_count
        FROM typifications t
        JOIN doc_typifications dt ON t.id = dt.typification_id
        WHERE t.deleted_at IS NULL
        GROUP BY t.name
        ORDER BY doc_count DESC;
    """
    return await conn.select(SCRIPT_SQL)


async def get_knowledge_tree_complexity(conn: Connection):
    SCRIPT_SQL = """
        SELECT
            t.name AS typification_name,
            COUNT(DISTINCT tax.id) AS taxonomy_count,
            COUNT(DISTINCT b.id) AS branch_count
        FROM typifications t
        LEFT JOIN taxonomies tax ON t.id = tax.typification_id
        LEFT JOIN branches b ON tax.id = b.taxonomy_id
        WHERE t.deleted_at IS NULL
        GROUP BY t.name
        ORDER BY taxonomy_count DESC, branch_count DESC;
    """
    return await conn.select(SCRIPT_SQL)


async def get_users_per_unit(conn: Connection):
    SCRIPT_SQL = """
        SELECT
            u.name,
            COUNT(us.id) AS user_count
        FROM units u
        LEFT JOIN users us ON u.id = us.unit_id
        GROUP BY u.name
        ORDER BY user_count DESC;
    """
    return await conn.select(SCRIPT_SQL)


async def get_activity_by_access_level(conn: Connection):
    SCRIPT_SQL = """
        SELECT
            access_level::text,
            COUNT(id) AS user_count
        FROM users
        GROUP BY access_level
        ORDER BY user_count DESC;
    """
    return await conn.select(SCRIPT_SQL)


async def get_most_used_sources(conn: Connection):
    SCRIPT_SQL = """
        WITH source_usage AS (
            SELECT source_id FROM typification_sources
            UNION ALL
            SELECT source_id FROM taxonomy_sources
        )
        SELECT
            s.name,
            COUNT(su.source_id) as usage_count
        FROM source_usage su
        JOIN sources s ON su.source_id = s.id
        WHERE s.deleted_at IS NULL
        GROUP BY s.name
        ORDER BY usage_count DESC
        LIMIT 10;
    """
    return await conn.select(SCRIPT_SQL)
