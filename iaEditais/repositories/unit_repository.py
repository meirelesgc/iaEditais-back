async def unit_post(conn, unit):
    params = unit.model_dump()
    SCRIPT_SQL = """
        INSERT INTO units (id, name, location, created_at)
        VALUES (%(id)s, %(name)s, %(location)s, %(created_at)s)
        """
    await conn.exec(SCRIPT_SQL, params)


async def unit_get(conn, id):
    one = False
    params = {}
    filters = str()

    if id:
        one = True
        params['id'] = id
        filters += 'AND u.id = %(id)s'

    SCRIPT_SQL = f"""
        SELECT u.id, u.name, u.location, u.created_at, u.updated_at
        FROM units u
        WHERE 1 = 1
            {filters}
        """
    return await conn.select(SCRIPT_SQL, params, one)
