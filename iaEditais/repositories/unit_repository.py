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


async def unit_put(conn, unit):
    params = unit.model_dump()
    SCRIPT_SQL = """
        UPDATE units
        SET name = %(name)s,
            location = %(location)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def unit_delete(conn, id):
    params = {'id': id}
    SCRIPT_SQL = """
        DELETE FROM units
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)
